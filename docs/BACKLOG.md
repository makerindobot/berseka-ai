# BERSEKA AI — Backlog & QA Gate Tracker

**Proyek:** BERSEKA (Bersih, Sehat, Kampung Asri) AI — Waste Sorting Compliance Monitoring
**Client:** Universitas Komputer Indonesia (UNIKOM) — Program KKN Kecamatan Coblong
**Dalang/Inisiator:** Daffa Jaya Perkasa — PT Makerindo Prima Solusi
**Deadline:** Minggu, 30 Agustus 2026 (PRODUKSI PENUH — dipakai warga nyata)
**Dibuat:** 27 Agustus 2026

---

## ⚠️ Catatan Risiko Jujur dari PM (Hermes)

Deadline ini SANGAT AGRESIF untuk scope penuh (dataset+training+backend+frontend+monitoring+deploy+dokumentasi ISO) dalam ~3 hari. PM akan all-out prioritaskan sesuai urutan backlog di bawah, dengan jalur kritis (critical path) diutamakan. Setiap kendala nyata akan dilaporkan jujur ke Daffa segera, bukan disembunyikan demi terlihat "selesai".

**Batasan token Kaggle:** limit tiap 5 jam — dipantau di setiap sesi training, dicatat di log training agar tidak boros.

---

## Status Legend
- 🔴 Belum mulai | 🟡 Sedang dikerjakan | 🟢 Selesai + Lolos QA | ⛔ Blocked

---

## BACKLOG 1 — Riset & Persiapan Dataset
**Role:** Dimas (Backend/ML Engineer) + PM
**Status:** 🟢 SELESAI — Lolos QC 1 (28 Agustus 2026). Dokumen: `docs/dataset/dataset-decision.md`

- [ ] Analisis dataset kandidat: TACO (YOLO format), Garbage Classification v2, Waste Segregation Image Dataset
- [ ] Tentukan skema label final: `ORGANIC` vs `NON_ORGANIC` (mapping dari kelas granular TACO ke 2 kelas utama)
- [ ] Split dataset: train/val/test (mis. 70/20/10), stratified agar tidak overfitting ke satu kelas
- [ ] Dokumentasi keputusan dataset di `docs/dataset-decision.md`

**QC 1 (Sari):** Verifikasi tidak ada label leakage antar split, distribusi kelas seimbang (rasio didokumentasikan), sumber dataset punya lisensi yang boleh dipakai komersial/riset.

---

## BACKLOG 2 — Arsitektur & Setup Training Pipeline (Kaggle)
**Role:** Dimas + Bayu (infra Kaggle)
**Status:** 🟡 Kode & pipeline selesai + teruji lokal (end-to-end dry-run CPU beneran jalan). BELUM push ke Kaggle & BELUM full training run GPU (menunggu koordinasi kuota dgn PM). Detail: `docs/architecture/training-pipeline.md`

- [x] Pilih arsitektur: YOLOv8 (ultralytics) — nano untuk dry-run, small untuk full run
- [x] Setup Kaggle Notebook terprogram via Kaggle API (`src/training/push_kaggle_kernel.py`, generate+push siap pakai, KAGGLE_API_TOKEN terverifikasi jalan)
- [x] Preprocessing: label mapping terpusat (`configs/label_mapping.yaml`), remap TACO, split anti-leakage (group-aware+stratifikasi ganda+dedup pHash), augmentasi field-condition — semua diuji dengan data sintetik & 3 unit test lulus (`tests/unit/test_preprocessing_pipeline.py`)
- [x] Skrip evaluasi metrik otomatis (mAP, precision, recall, F1, confusion matrix, loss curve, gate vs target Backlog 1) — diuji end-to-end
- [ ] Definisikan output model: bounding box + klasifikasi organik/anorganik + confidence score (skema sudah ada di data.yaml biner, kontrak output API belum dikerjakan — Backlog 6)
- [ ] Implementasi estimasi volume (Liter/Kg) — di luar scope Backlog 2, lihat Backlog 3
- [ ] **BELUM**: download penuh dataset gabungan, EDA volume nyata, push notebook ke Kaggle, full training run GPU

**QC 2 (Sari):** Review notebook menghasilkan output sesuai schema kontrak (`detectedType`, `confidenceScore`, `estimatedVolumeLiter`, `organik_percent`, `non_organik_percent`, `detections[]`).

---

## BACKLOG 3 — Kalibrasi Kamera & Validasi Estimasi Volume (KRITIKAL)
**Role:** Dimas + Nara (UX untuk instruksi pengguna)
**Status:** 🟡 Dokumen riset & formula v1 selesai (disusun Nara), **TEORITIS — belum divalidasi data lapangan**. Belum diintegrasikan ke kode/endpoint mana pun. Detail: `docs/architecture/camera-calibration.md`.

Sesuai arahan atasan Daffa: harus ada validasi antara "bacaan kamera+AI" vs pengukuran manual, dan jarak/posisi kamera optimal.

- [x] Tentukan rentang jarak kamera optimal — **30–50cm, tampak atas tegak lurus**, diturunkan dari perhitungan geometris (FOV kamera HP ~65° efektif × ukuran tong 10–50L). 🔴 Nilai FOV & rasio tong adalah estimasi riset publik, **belum diverifikasi dengan HP/tong sungguhan warga Coblong**.
- [x] Definisikan aturan confidence turun di luar rentang optimal — formula `quality_multiplier(area_ratio, bbox_touches_edge)`: rentang aman `area_ratio` 15%-50%, di luar itu turun linear ke floor 0.3, bbox nyentuh tepi = blokir total (`multiplier=0.0`). 🟡 Threshold berbasis matematis, belum di-tuning empiris.
- [x] Tabel kalibrasi volume awal (v1) — formula `estimated_volume_liter = 1.73e-9 × (bbox_area_px)^1.5`, dikalibrasi pada titik referensi jarak 40cm & resolusi 4000×3000px. 🔴 **Margin error sistematis ±20-25% disadari sendiri oleh penulis** akibat asumsi jarak tetap (rentang optimal sebenarnya 30-50cm, bukan titik 40cm) — wajib direvisi begitu ada data lapangan.
- [x] Panduan foto untuk warga (Bahasa Indonesia awam) — 6 langkah + tooltip singkat, siap dipakai UI (Backlog 8), termasuk instruksi eksplisit "pakai kamera 1x, bukan wide" untuk menghindari distorsi lensa.
- [ ] **Belum dikerjakan**: rencana validasi lapangan (§7 dokumen) baru berupa RENCANA, belum dieksekusi — perlu foto & ukur manual 10-15 tong nyata Coblong begitu data collector-bot mulai masuk (lihat `field-data-collection-plan.md`).

**QC 3 (Sari):** Uji dengan sample foto pada jarak bervariasi, verifikasi estimasi volume konsisten dalam toleransi wajar (%error terdokumentasi). **BELUM BISA DIEKSEKUSI** — menunggu foto lapangan nyata Coblong (collector-bot sedang tahap pengumpulan, lihat `field-data-collection-plan.md`).

**Catatan jujur untuk QC:** dokumen ini SENGAJA ditandai penulis sendiri dengan sistem warna 🟢/🟡/🔴 per klaim (riset terverifikasi / turunan matematis / wajib divalidasi) — semua angka jarak, formula volume, dan threshold confidence berstatus 🟡 atau 🔴, TIDAK ADA yang sudah tervalidasi dengan data lapangan asli. Jangan dianggap "selesai" produksi sampai QC 3 tercapai dengan data nyata.

---

## BACKLOG 4 — Antisipasi Kondisi Lapangan Non-Ideal
**Role:** Dimas
**Status:** 🟡 Modul validasi kualitas foto selesai + 9 unit test lulus (diverifikasi ulang oleh PM, semua PASS). **BELUM diverifikasi dgn foto lapangan asli, BELUM diintegrasikan ke endpoint `/predict`** (Backlog 6 sudah live tapi belum memanggil modul ini) — item confidence & augmentation training belum dikerjakan. Detail: `docs/architecture/image-quality-gate.md`

Sesuai poin #14 brief: kamera buram, tidak stabil, jarak tidak konsisten.

- [x] Deteksi blur (Laplacian variance / sharpness threshold) → tolak foto buram sebelum inference — `src/preprocessing/image_quality_check.py`, threshold 100 (verifikasi empiris di `docs/architecture/image-quality-gate.md` §2.3), diuji `tests/unit/test_image_quality_check.py` (PASS)
- [x] Deteksi foto gelap/pencahayaan buruk → minta foto ulang — implementasi sama (brightness histogram + rasio clipped-pixel, threshold 40–215/255), diuji & PASS
- [x] Deteksi resolusi terlalu rendah (item tambahan di luar checklist asli, ditambahkan karena ada di scope tugas) — min sisi terpendek 320px, diuji & PASS
- [ ] Validasi confidence < 40% → error `NO_WASTE_DETECTED` — **sudah diimplementasikan di sisi lain** (Backlog 6, `api/routes/predict.py`), TAPI belum terhubung dengan modul quality-gate ini — saat ini `/predict` menerima foto buram/gelap apa adanya tanpa ditolak duluan oleh gate kualitas. **Perlu kerja integrasi lanjutan**: panggil `check_image_quality()` di awal handler `/predict` sebelum masuk ke classifier.
- [ ] Data augmentation saat training: motion blur, brightness variation, rotasi ringan, agar model robust terhadap kondisi lapangan nyata — **belum dikerjakan khusus untuk Backlog 4**; augmentasi umum untuk training sudah ada di `src/preprocessing/augmentation.py` (Backlog 2) tapi belum divalidasi khusus terhadap requirement Backlog 4 ini

**QC 4 (Sari):** Uji dengan set foto sengaja buram/miring/gelap, verifikasi sistem menolak dengan pesan jelas, bukan memberi hasil ngawur.
**Catatan jujur untuk QC:** unit test memakai gambar SINTETIK (dibuat dgn PIL/NumPy: warna solid, checkerboard+noise, gambar sangat gelap/terang), BUKAN foto lapangan asli — karena foto real warga Coblong belum tersedia (lihat gap di `dataset-decision.md` §7). Threshold blur & pencahayaan defensible secara teknis (riset + eksperimen numerik terdokumentasi) tapi direkomendasikan dikalibrasi ulang begitu foto lapangan asli tersedia, sebelum dianggap final untuk audit klien. **Modul ini juga masih BERDIRI SENDIRI, belum tersambung ke endpoint /predict** — celah ini harus ditutup sebelum Backlog 4 dianggap benar-benar selesai fungsional (bukan cuma modul terisolasi yang lolos unit test).

---

## BACKLOG 5 — Training Model Awal (Kaggle GPU)
**Role:** Dimas
**Status:** 🔴

- [ ] Training run 1 (baseline) — catat metrik: precision, recall, mAP, confusion matrix
- [ ] Evaluasi overfitting/underfitting (train vs val loss curve)
- [ ] Tuning hyperparameter jika perlu (learning rate, epoch, augmentation)
- [ ] Export model final (format ONNX/TorchScript untuk serving efisien)

**QC 5 (Sari):** Model harus capai target metrik minimum (mAP dan akurasi disepakati sebelum training — TBD bersama Daffa), tidak overfit (val loss tidak jauh dari train loss).

---

## BACKLOG 6 — Model Serving API (FastAPI, sesuai kontrak existing)
**Role:** Dimas
**Status:** 🟡 Endpoint `/predict` & `/ws/predict` selesai + berjalan nyata dgn MOCK classifier (model YOLOv8 asli Backlog 5 belum ada). 20/20 test lulus (8 test integrasi API baru + 12 test lama). Diverifikasi juga dengan live server sungguhan (uvicorn + curl + client WebSocket nyata), bukan cuma test harness. Kode: `api/main.py`, `api/routes/predict.py`, `api/routes/ws_predict.py`, `api/schemas/predict_schema.py`, `api/services/mock_classifier.py`, `api/services/image_annotator.py`.

- [x] Implementasi endpoint `/predict` (HTTP, multipart image) — field kontrak: `requestId`, `detectedType`, `confidenceScore`, `estimatedVolumeLiter`, `organik_percent`, `non_organik_percent`, `detections[]`, `vendorName`, `annotatedImageBase64`. Diuji dgn curl sungguhan ke server live (`uvicorn api.main:app`), respons sesuai skema.
- [x] Implementasi endpoint `/ws/predict` (WebSocket realtime) dengan `serverLatencyMs` — protokol binary frame per pesan, balasan JSON per frame, koneksi tetap hidup pada error (tidak reconnect tiap frame). Diuji dgn client `websockets` nyata: 3 frame berurutan, `serverLatencyMs` terukur nyata (~104–178ms di CPU gateway, BUKAN hardcode).
- [x] Error handling: `NO_WASTE_DETECTED` sesuai contract, HTTP 200 dgn body error terstruktur (bukan 5xx) — dipicu saat confidence mock < 40%; diverifikasi lolos terpicu di test (`test_predict_many_requests_eventually_hits_no_waste_detected`).
- [ ] Optimasi latency (target: respons cepat/near real-time sesuai permintaan poin #13) — **belum jadi fokus sesi ini**; latency saat ini didominasi delay buatan mock (~50–180ms) yang mensimulasikan compute time, BUKAN representasi latency model asli — perlu diukur ulang setelah model YOLOv8 nyata (Backlog 5) di-plug-in.

**Catatan jujur untuk QC (Sari):** classifier di balik endpoint ini adalah **MOCK** (heuristik warna dominan gambar + random jitter, `api/services/mock_classifier.py`) — SENGAJA, sesuai instruksi, karena model YOLOv8 asli belum selesai training (Backlog 5). Kontrak I/O (skema request/response) sudah final & stabil, tapi hasil klasifikasi TIDAK merepresentasikan akurasi model asli — jangan dipakai untuk menilai kualitas AI, hanya untuk menguji integrasi Backend (Backlog 7)/Frontend (Backlog 8) terhadap kontrak API. Swap ke model asli nanti hanya perlu ganti `MockClassifier` di `routes/predict.py` & `routes/ws_predict.py`, skema tidak berubah.

**QC 6 (Sari):** Uji load — response time diukur dan didokumentasikan (klaim "nano second" tidak mungkin literal untuk inference CV — PM akan luruskan definisi target performa dengan Daffa; realistisnya target low-latency dalam hitungan ratusan ms).

---

## BACKLOG 7 — Backend Node.js Integration (Adapter Pattern)
**Role:** Dimas + Raka
**Status:** 🟡 Backend Node.js + Adapter Pattern selesai & teruji end-to-end sungguhan (Backend → FastAPI Backlog 6 → Mock AI → SQLite → response), 15/15 test lulus. Integrasi Raka (frontend, Backlog 8) belum dimulai. Kode: `backend/` (lihat `backend/README.md`).

- [x] Implementasi `IWasteAiAdapter` — **CATATAN PENTING**: tidak ditemukan dokumen interface asli terpisah dari Daffa di repo saat Backlog 7 dimulai, jadi Dimas menyusun kontrak ini sendiri berdasarkan skema `/predict` Backlog 6 (`backend/src/adapters/IWasteAiAdapter.js`). **Perlu review & sign-off Daffa** sebelum dianggap final, terutama method `analyzeImage()`/`healthCheck()` dan bentuk `WasteAiPredictionResult`. Implementasi: `FastApiWasteAiAdapter` (panggil Model Serving API sungguhan) + `MockWasteAiAdapter` (testing tanpa FastAPI) + factory berbasis env var.
- [x] Integrasi ke sistem monitoring tata kelola sampah — endpoint `POST /api/scan` (analisis 1 foto → simpan histori → response), `GET /api/scans`, `GET /api/compliance/:kelompokKknId`. Modul monitoring KKN (progres mahasiswa) **belum dikerjakan** — di luar scope sesi ini, brief hanya eksplisit soal modul tata kelola sampah.
- [x] Skema database histori scan (`backend/src/db/schema.js`, SQLite via `node:sqlite` bawaan Node — sengaja tanpa native addon/DB server terpisah, hemat RAM gateway) — tabel `scans` (per warga/tong/waktu) + `scan_windows` (jadwal pagi/sore, **jam default 05:00-09:00 & 15:00-18:00 indikatif, perlu konfirmasi Daffa** untuk jam pasti program Coblong).
- [x] Validasi jadwal scan otomatis pagi/sore — `backend/src/lib/scanWindow.js`, `determineScanWindow()` menentukan window aktif berdasarkan waktu request; diuji dgn kasus batas tepat (inclusive boundary), di luar & di dalam rentang.

**QC 7 (Sari):** Uji integrasi end-to-end: foto masuk → model → backend → tersimpan → dapat ditarik untuk laporan kepatuhan. **Sudah diverifikasi sungguhan** (bukan cuma test harness/mock): FastAPI Backlog 6 & backend Node.js dijalankan bersamaan (`WASTE_AI_ADAPTER=fastapi`), foto dikirim via curl ke `POST /api/scan`, hasil tersimpan di SQLite, diambil ulang via `GET /api/scans` & `GET /api/compliance/:id` — data konsisten end-to-end (3 scan test, avgOrganikPercent terhitung benar 97.53%).

**Catatan jujur untuk QC:** endpoint `POST /api/scan` saat ini TIDAK ada autentikasi/otorisasi — siapa saja bisa hit endpoint ini, perlu diamankan sebelum Backlog 11 (deploy produksi). `annotatedImageBase64` belum diupload ke object storage (baru flag di DB, base64 penuh tidak disimpan permanen agar tidak membebani disk gateway) — perlu iterasi lanjutan.

---

## BACKLOG 8 — Frontend Monitoring Dashboard
**Role:** Raka + Nara
**Status:** 🔴

- [ ] Dashboard sederhana untuk monitoring performa AI (metrik training/re-training)
- [ ] Fitur uji model manual: upload/scan kamera langsung dari browser
- [ ] Visualisasi kepatuhan warga per RT/RW/Kecamatan Coblong (dashboard tata kelola sampah)
- [ ] Visualisasi monitoring progres KKN mahasiswa

**QC 8 (Sari):** Uji semua fitur dashboard berfungsi, responsif, data akurat sesuai backend.

---

## BACKLOG 9 — Continuous Re-training Pipeline (Konsep Berkelanjutan)
**Role:** Dimas + Bayu
**Status:** 🔴

Sesuai poin #12: model harus bisa di-retrain berkelanjutan dari data real lapangan.

- [ ] Pipeline untuk mengumpulkan data hasil scan asli warga (dengan consent/anonimisasi)
- [ ] Mekanisme retraining terjadwal atau manual-trigger dari dashboard
- [ ] Versioning model (v1, v2, dst) dengan tracking metrik antar versi

**QC 9 (Sari):** Simulasi 1 siklus retraining end-to-end (data baru → retrain → model v2 → perbandingan metrik).

---

## BACKLOG 10 — Setup GitHub Repository & Dokumentasi Standar
**Role:** Bayu + PM
**Status:** 🔴

- [ ] Buat repo `makerindobot/berseka-ai` (public/private — konfirmasi ke Daffa)
- [ ] Struktur folder sesuai konvensi standar (mengacu konvensi umum ML project: `data/`, `models/`, `src/`, `api/`, `docs/`, `tests/`, `notebooks/`)
- [ ] README.md lengkap: latar belakang, arsitektur, cara install, cara pakai, kredit (Daffa Jaya Perkasa sebagai inisiator, tanpa berlebihan)
- [ ] `docs/` — dokumen teknis: arsitektur sistem, keputusan model, API reference, panduan kontribusi (agar developer lain bisa lanjutkan / open source-ready)
- [ ] Commit history mengikuti Conventional Commits + co-author Daffa (standar Damaker Studio)

**QC 10 (Sari):** README dapat diikuti orang baru tanpa penjelasan tambahan; struktur folder konsisten dan terdokumentasi.

---

## BACKLOG 11 — Deployment ke VPS (Jika Model Layak Pakai)
**Role:** Bayu
**Status:** 🔴 (Menunggu Backlog 5-6 lolos QA dulu)

- [ ] Kriteria "layak pakai" disepakati dulu dengan Daffa (metrik minimum model + hasil QA lapangan)
- [ ] Setup deployment (containerized/serving di VPS terpisah dari gateway — gateway TIDAK punya GPU, perlu keputusan server serving terpisah bila model besar)
- [ ] Setup monitoring uptime & performa API produksi

**QC 11 (Sari):** Uji API produksi dari luar (bukan localhost), verifikasi stabil di bawah beban wajar.

---

## Dependency Chain (Urutan Wajib)

```
1 (Dataset) → 2 (Training pipeline) → 3 (Kalibrasi) → 4 (Robustness) → 5 (Training run)
    → 6 (Serving API) → 7 (Backend integration) → 8 (Frontend) 
    → 9 (Retraining pipeline) ⇄ 10 (Repo & Docs, bisa paralel dari awal)
    → 11 (Deploy produksi, gate terakhir)
```

**Catatan:** Backlog 10 (repo & docs) berjalan PARALEL sejak awal, bukan menunggu di akhir — supaya tiap progress ter-commit bertahap dan bisa direview kapan saja.

---

## Keputusan Resmi (Dikonfirmasi Daffa, 27 Agustus 2026)

1. **Target metrik minimum model** — ditentukan PM/tim sesuai standar internasional computer vision untuk klasifikasi biner + deteksi objek:
   - mAP@0.5 ≥ **0.85**
   - Akurasi klasifikasi (organik vs non-organik) ≥ **90%**
   - Precision & Recall seimbang (F1-score ≥ 0.85), tidak boleh timpang ke satu kelas
   - Val loss tidak boleh menyimpang > 15% dari train loss (indikasi anti-overfitting)
2. **"Response time nano second"** — klarifikasi: ini merujuk pada **responsivitas web dashboard** (Backlog 8), bukan literal kecepatan inference model. Target: UI dashboard responsif (< 100ms untuk interaksi UI, loading state jelas untuk proses async seperti scan/predict).
3. **Repo GitHub:** **Public** — `makerindobot/berseka-ai`, mendukung tujuan portofolio & open-source sesuai poin #17 brief.
4. **Server model serving produksi:** Training tetap di Kaggle (GPU cloud). Untuk deployment produksi, PM/Bayu akan riset dan berikan rekomendasi platform + estimasi biaya setelah model lolos QC 5 (lihat Backlog 11).
