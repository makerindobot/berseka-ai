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
**Status:** 🟡

- [ ] Analisis dataset kandidat: TACO (YOLO format), Garbage Classification v2, Waste Segregation Image Dataset
- [ ] Tentukan skema label final: `ORGANIC` vs `NON_ORGANIC` (mapping dari kelas granular TACO ke 2 kelas utama)
- [ ] Split dataset: train/val/test (mis. 70/20/10), stratified agar tidak overfitting ke satu kelas
- [ ] Dokumentasi keputusan dataset di `docs/dataset-decision.md`

**QC 1 (Sari):** Verifikasi tidak ada label leakage antar split, distribusi kelas seimbang (rasio didokumentasikan), sumber dataset punya lisensi yang boleh dipakai komersial/riset.

---

## BACKLOG 2 — Arsitektur & Setup Training Pipeline (Kaggle)
**Role:** Dimas + Bayu (infra Kaggle)
**Status:** 🔴

- [ ] Pilih arsitektur: YOLOv8 (segmentation/detection) — proven untuk TACO dataset
- [ ] Setup Kaggle Notebook terprogram via Kaggle API (dijalankan dari gateway, dipantau limit token/GPU quota)
- [ ] Definisikan output model: bounding box + klasifikasi organik/anorganik + confidence score
- [ ] Implementasi estimasi volume (Liter/Kg) berdasarkan area bounding box relatif terhadap volume tong sampah yang diinput user — BUTUH kalibrasi jarak & posisi kamera (lihat Backlog 3)

**QC 2 (Sari):** Review notebook menghasilkan output sesuai schema kontrak (`detectedType`, `confidenceScore`, `estimatedVolumeLiter`, `organik_percent`, `non_organik_percent`, `detections[]`).

---

## BACKLOG 3 — Kalibrasi Kamera & Validasi Estimasi Volume (KRITIKAL)
**Role:** Dimas + Nara (UX untuk instruksi pengguna)
**Status:** 🔴

Sesuai arahan atasan Daffa: harus ada validasi antara "bacaan kamera+AI" vs pengukuran manual, dan jarak/posisi kamera optimal.

- [ ] Tentukan rentang jarak kamera optimal (mis. 30-50cm tampak atas) berdasarkan riset + uji coba
- [ ] Definisikan aturan: foto di luar rentang optimal → confidence otomatis diturunkan / ditandai "kualitas rendah"
- [ ] Buat tabel kalibrasi volume tong vs area piksel terdeteksi
- [ ] Dokumentasi panduan foto untuk warga (jarak, pencahayaan, sudut) — jadi bagian UX aplikasi

**QC 3 (Sari):** Uji dengan sample foto pada jarak bervariasi, verifikasi estimasi volume konsisten dalam toleransi wajar (%error terdokumentasi).

---

## BACKLOG 4 — Antisipasi Kondisi Lapangan Non-Ideal
**Role:** Dimas
**Status:** 🔴

Sesuai poin #14 brief: kamera buram, tidak stabil, jarak tidak konsisten.

- [ ] Deteksi blur (Laplacian variance / sharpness threshold) → tolak foto buram sebelum inference
- [ ] Deteksi foto gelap/pencahayaan buruk → minta foto ulang
- [ ] Validasi confidence < 40% → error `NO_WASTE_DETECTED` (sudah sesuai contract)
- [ ] Data augmentation saat training: motion blur, brightness variation, rotasi ringan, agar model robust terhadap kondisi lapangan nyata

**QC 4 (Sari):** Uji dengan set foto sengaja buram/miring/gelap, verifikasi sistem menolak dengan pesan jelas, bukan memberi hasil ngawur.

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
**Status:** 🔴

- [ ] Implementasi endpoint `/predict` (HTTP, multipart image) sesuai schema yang sudah diberikan Daffa
- [ ] Implementasi endpoint `/ws/predict` (WebSocket realtime) dengan `serverLatencyMs`
- [ ] Optimasi latency (target: respons cepat/near real-time sesuai permintaan poin #13)
- [ ] Error handling: `NO_WASTE_DETECTED` sesuai contract

**QC 6 (Sari):** Uji load — response time diukur dan didokumentasikan (klaim "nano second" tidak mungkin literal untuk inference CV — PM akan luruskan definisi target performa dengan Daffa; realistisnya target low-latency dalam hitungan ratusan ms).

---

## BACKLOG 7 — Backend Node.js Integration (Adapter Pattern)
**Role:** Dimas + Raka
**Status:** 🔴

- [ ] Implementasi `IWasteAiAdapter` sesuai interface existing yang diberikan Daffa
- [ ] Integrasi ke sistem monitoring KKN & tata kelola sampah (dua modul utama sesuai brief)
- [ ] Skema database untuk histori scan per warga/tong sampah/waktu (pagi/sore terjadwal)
- [ ] Validasi jadwal scan otomatis (sistem menentukan waktu pagi/sore)

**QC 7 (Sari):** Uji integrasi end-to-end: foto masuk → model → backend → tersimpan → dapat ditarik untuk laporan kepatuhan.

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
