# BERSEKA AI — Arsitektur & Strategi Training Pipeline (Backlog 2)

| | |
|---|---|
| **Proyek** | BERSEKA AI — Sistem Monitoring Kepatuhan Pemilahan Sampah, Kec. Coblong (kerja sama UNIKOM) |
| **Dokumen** | `docs/architecture/training-pipeline.md` |
| **Disusun oleh** | Dimas — Backend/ML Engineer, Damaker Studio |
| **Status** | Pipeline & kode siap, **BELUM** menjalankan full training run (butuh koordinasi jadwal kuota Kaggle dgn PM) |
| **Acuan dataset** | `docs/dataset/dataset-decision.md` (Backlog 1, final) |

---

## 1. Ringkasan Arsitektur

```
Kaggle Dataset (6 sumber publik, lihat dataset-decision.md)
        │
        ▼
src/preprocessing/dataset_acquisition.py   → download via Kaggle API (KAGGLE_API_TOKEN)
        │
        ▼
src/preprocessing/remap_taco_labels.py     → TACO 60 kelas → ORGANIC/NON_ORGANIC
        │                                     (pakai configs/label_mapping.yaml, single source of truth)
        ▼
src/preprocessing/split_dataset.py         → group-aware + stratified ganda + dedup pHash
        │                                     (anti-leakage sesuai §5 dataset-decision.md)
        ▼
src/preprocessing/augmentation.py          → augmentasi field-condition (Albumentations)
        │                                     + augmentasi bawaan YOLOv8 (mosaic/mixup/hsv) saat training
        ▼
src/training/train.py                      → training YOLOv8 (ultralytics), mode dry_run/full_run
        │                                     checkpoint & resume otomatis
        ▼
src/training/evaluate.py                   → mAP, precision, recall, F1, confusion matrix,
                                              loss curve, gate lolos/tidak vs target Backlog 1
```

Notebook yang dijalankan di Kaggle **tidak ditulis manual** — di-generate & di-push terprogram
oleh `src/training/push_kaggle_kernel.py` dari kode di atas, supaya notebook selalu sinkron
dengan source repo (bukan 2 sumber kebenaran yang bisa divergen).

---

## 2. Setup Kaggle API (format token baru)

- Auth memakai `KAGGLE_API_TOKEN` (format token baru Kaggle), dibaca dari env var atau
  file `~/.kaggle/access_token` — **bukan** `username`/`key` (`kaggle.json`) lama.
- Gateway lokal sudah terkoneksi & terverifikasi (lihat §6 Status Verifikasi).
- Kernel Kaggle sendiri otomatis punya kredensial Kaggle internal untuk akses dataset
  yang di-attach — token gateway hanya dipakai untuk push kernel & download dataset
  dari gateway saat verifikasi lokal.

---

## 3. GPU yang Tersedia di Kaggle

Kaggle akun free biasanya menawarkan pilihan accelerator saat kernel dijalankan:
- **GPU T4 x2** — 2x NVIDIA T4 (16GB masing-masing), umumnya lebih cepat untuk workload
  yang bisa memanfaatkan multi-GPU atau batch besar.
- **GPU P100** — 1x NVIDIA P100 (16GB), throughput single-GPU lebih tinggi per-card
  dibanding T4, tapi tidak ada paralelisme.

**Rekomendasi**: mulai dengan **P100** untuk baseline (single-GPU, lebih sederhana untuk
debug), pertimbangkan **T4 x2** hanya jika training script sudah disesuaikan untuk
DataParallel/DDP — ultralytics YOLOv8 mendukung multi-GPU otomatis lewat `device=0,1`,
tapi harus diuji ketimbang diasumsikan bekerja tanpa isu OOM/batch-size split.

Accelerator dipilih di UI Kaggle kernel (tidak sepenuhnya bisa dipaksa 100% via API —
`enable_gpu: true` di `kernel-metadata.json` mengaktifkan slot GPU, tapi tipe GPU
default mengikuti pengaturan/ketersediaan akun saat itu; verifikasi manual di UI
sebelum trigger run penting kalau butuh tipe spesifik).

---

## 4. Strategi Kuota Kaggle (KRITIKAL — batasan nyata)

### 4.1 Batasan yang diketahui
- **GPU quota**: ~30 jam GPU/minggu untuk akun free (reset mingguan).
- **API request limit**: dibatasi tiap 5 jam (per info Daffa) — jangan spam kernel
  push/status-check berulang dalam window pendek.

### 4.2 Aturan wajib penggunaan kuota
1. **Dry-run dulu, selalu.** `training_config.yaml → training.dry_run` memakai
   `yolov8n.pt` (model terkecil), subset 2% data, 3 epoch, sebelum full run apa pun.
   Tujuannya memvalidasi: data.yaml valid, label mapping benar, tidak ada bug shape/OOM,
   augmentasi tidak crash — SEMUA divalidasi dengan durasi menit, bukan jam.
2. **Checkpoint/resume wajib, bukan opsional.** `training.full_run.save_period=5` (checkpoint
   tiap 5 epoch). Checkpoint (`last.pt`) disimpan ke `/kaggle/working/checkpoints`, lalu
   **wajib** di-upload sebagai Kaggle Dataset `<username>/berseka-checkpoints` (`kaggle
   datasets version -p /kaggle/working/checkpoints -m "epoch N"`) di akhir tiap sesi kernel.
   Sesi berikutnya attach dataset ini sebagai kernel input dan `train.py --resume` otomatis
   melanjutkan dari `last.pt`, TIDAK dari nol.
3. **Epoch dibatasi bertahap.** Full run tidak langsung 100 epoch dalam 1 sesi kalau
   estimasi durasi mendekati batas sesi kernel Kaggle (~9 jam/sesi, terpisah dari kuota
   30 jam/minggu). Pecah jadi beberapa sesi ber-resume, dipantau via `results.csv`.
4. **Batasi frekuensi API call.** Kernel push, status polling (`kaggle kernels status`),
   dataset version — semua dikelompokkan, tidak dipanggil berulang dalam loop pendek.
   Skrip di `src/training/push_kaggle_kernel.py` push 1x per iterasi kerja, bukan
   otomatis retry cepat.
5. **Log pemakaian kuota di sini setiap sesi training** (lihat §5 Log Pemakaian Kuota
   di bawah — WAJIB diisi tim setiap kali menjalankan run GPU sungguhan).

### 4.3 Estimasi rencana full training run
| Tahap | Model | Epoch | Estimasi durasi (P100) | Kuota terpakai (indikatif) |
|---|---|---|---|---|
| Dry-run validasi pipeline | yolov8n | 3 | 5–10 menit | <0.2 jam |
| Full run tahap 1 (baseline) | yolov8s | 40 (checkpoint tiap 5) | ~3–5 jam (tergantung ukuran dataset final) | 3–5 jam |
| Full run tahap 2 (lanjutan, resume) | yolov8s | +40 (s.d. patience/early-stop) | ~3–5 jam | 3–5 jam |
| Evaluasi + tuning ulang bila belum lolos gate | yolov8s | +20–40 | ~2–4 jam | 2–4 jam |
| **Total indikatif** | | | | **~10–18 jam** dari kuota 30 jam/minggu — sisakan buffer untuk debugging tak terduga |

Angka di atas **indikatif**, akan direvisi setelah EDA volume data final (Backlog 2 lanjutan)
diketahui — ukuran dataset gabungan final belum di-lock karena undersampling/oversampling
(§4.2 dataset-decision.md) baru final setelah semua dataset ditarik & dihitung distribusinya.

### 4.4 Log Pemakaian Kuota (isi tiap sesi run GPU sungguhan)
| Tanggal | Sesi/kernel version | Mode | GPU dipakai | Durasi | Sisa kuota mingguan (approx) | Catatan |
|---|---|---|---|---|---|---|
| _(belum ada run GPU sungguhan — pipeline baru divalidasi lokal CPU, lihat §6)_ | | | | | | |

---

## 5. Alur Kerja Operasional (Runbook)

1. **Lokal (gateway)**: jalankan `python -m src.training.push_kaggle_kernel --username makerindo --mode dry_run` untuk generate `notebooks/kaggle_kernel/`. Tambahkan `--push` untuk push ke Kaggle.
2. **Sebelum push pertama kali**: upload source code repo sebagai Kaggle Dataset
   `makerindo/berseka-src` (`kaggle datasets create -p src/ ...` atau via UI) — kernel
   men-`sys.path.insert` dataset ini alih-alih clone git tiap run.
3. **Di Kaggle UI**: pilih accelerator (P100/T4x2), jalankan kernel manual pertama kali
   (mode `dry_run` by default via env var `NOTEBOOK_MODE`) — verifikasi log tidak error.
4. **Setelah dry-run lolos**: ubah `NOTEBOOK_MODE=full_run` di kernel settings, commit run.
5. **Tiap sesi selesai/mendekati limit**: upload checkpoint terbaru ke Kaggle Dataset
   `berseka-checkpoints`, catat di §4.4 Log Pemakaian Kuota.
6. **Setelah training dianggap cukup**: `src/training/evaluate.py` otomatis jalan di
   notebook (sel terakhir), hasil `evaluation_report.json` dicek terhadap gate —
   bila `overall_pass: false`, kembali ke tuning (augmentasi/hyperparameter) sebelum
   run tambahan, JANGAN langsung buka sesi GPU baru tanpa analisis root-cause.

---

## 6. Status Verifikasi (kejujuran progres)

✅ **Sudah diverifikasi jalan nyata:**
- Autentikasi Kaggle API dengan `KAGGLE_API_TOKEN` format baru — berhasil (`api.authenticate()` OK).
- Ketersediaan seluruh 6 dataset sumber (TACO YOLO, TACO COCO, Garbage Classification v2,
  Alistairking, RealWaste, Waste Segregation) — terverifikasi via `kaggle datasets metadata`.
- `configs/label_mapping.yaml` — dimuat & di-resolve dengan benar (unit test manual: TACO
  "Food waste"→ORGANIC, "Clear plastic bottle"→NON_ORGANIC, "Other litter"→drop, dst).
- `src/preprocessing/remap_taco_labels.py` — diuji dengan dataset TACO sintetik (mock
  data.yaml + label files), hasil remap bbox & drop kelas ambigu sesuai ekspektasi.
- `src/preprocessing/split_dataset.py` — diuji dengan 300 sample sintetik (3 sumber x 2 kelas
  x grup 3-foto), hasil split 70/15/15 per grup, **0 group leakage terverifikasi eksplisit**.
- `src/preprocessing/augmentation.py` — pipeline Albumentations (7 operasi: motion blur,
  gaussian blur/noise, jpeg artifact, brightness/contrast, occlusion, hue shift) berhasil
  dibangun & dijalankan pada gambar dummy.
- `src/training/train.py` + `src/training/evaluate.py` — **dijalankan end-to-end sungguhan**
  di CPU gateway lokal dengan dataset sintetik 16 gambar (bukan mock/simulasi kode): YOLOv8n
  1 epoch training beneran jalan, checkpoint `best.pt`/`last.pt` dihasilkan, evaluasi
  menghasilkan `evaluation_report.json` dengan metrik & gate check yang benar secara logika
  (metrik 0 karena hanya 1 epoch/data sintetik — bukan bug, expected untuk smoke test).
- `src/training/push_kaggle_kernel.py` — notebook `.ipynb` + `kernel-metadata.json`
  ter-generate valid (11 sel, JSON valid, referensi 6 dataset + berseka-src + berseka-checkpoints).

⚠️ **BELUM dilakukan (di luar scope aman untuk sesi ini):**
- **Push notebook ke Kaggle & jalankan di GPU Kaggle sungguhan** — sengaja tidak dilakukan
  karena instruksi eksplisit untuk tidak menjalankan training penuh/berjam-jam tanpa
  koordinasi PM soal timing kuota. Push (`--push`) sudah siap dipakai kapan saja disetujui.
- **Upload dataset `berseka-src` dan `berseka-checkpoints` ke Kaggle** — perlu dilakukan
  sebelum kernel pertama bisa jalan penuh di Kaggle (kernel butuh akses source code).
- **Download penuh & EDA volume data gabungan sesungguhnya** — hanya metadata yang
  diverifikasi, belum download penuh (volume besar, berpotensi makan waktu/kuota API).
- **Full training run GPU** — belum dijalankan sama sekali, keputusan bersama PM soal jadwal.

---

## 7. Kendala & Risiko Terbuka

1. **Estimasi durasi & jumlah iterasi full run masih indikatif** (§4.3) — akan direvisi
   setelah volume data final diketahui (butuh Backlog 2 lanjutan: EDA nyata pasca-download).
2. **Tipe GPU (T4x2 vs P100) tidak 100% terkontrol dari API** — dipilih manual di Kaggle UI,
   perlu koordinasi siapa yang memicu run supaya konsisten.
3. **Alistairking taksonomi 30 kelas** di `label_mapping.yaml` ditulis berdasar nama folder
   umum dataset ini — **wajib diverifikasi ulang nama persis saat akuisisi penuh** (ditandai
   di file konfigurasi), karena README publik tidak selalu 1:1 dengan struktur folder aktual.
4. **Lisensi beberapa dataset belum final** (lihat §6 dataset-decision.md) — tidak menghalangi
   pipeline teknis, tapi gate legal sebelum rilis produksi tetap perlu dituntaskan tim PM/legal.
