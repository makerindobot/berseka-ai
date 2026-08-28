# BERSEKA AI

**Bersih, Sehat, Kampung Asri** — Sistem Monitoring Kepatuhan Pemilahan Sampah berbasis AI untuk Kecamatan Coblong.

> 🚧 **Status: Dalam Pengembangan Aktif** — proyek ini sedang dalam tahap awal (dataset & training pipeline). Lihat [`docs/BACKLOG.md`](docs/BACKLOG.md) untuk progres detail.

## Tentang Proyek

BERSEKA adalah sistem AI yang dikembangkan untuk mendukung program Kuliah Kerja Nyata (KKN) mahasiswa di Kecamatan Coblong, bekerja sama dengan **Universitas Komputer Indonesia (UNIKOM)**. Sistem ini terdiri dari dua modul utama:

1. **Monitoring KKN** — pemantauan aktivitas dan progres mahasiswa KKN di lapangan.
2. **Monitoring Tata Kelola Sampah** — mengukur seberapa patuh warga terhadap pemilahan sampah organik dan anorganik menggunakan computer vision.

Warga memindai (scan) tong sampah mereka pada jadwal yang ditentukan sistem (pagi & sore). Model AI menganalisis foto tampak atas tong sampah untuk:
- Mendeteksi & memberi bounding box pada sampah organik vs anorganik
- Mengestimasi volume/berat sampah
- Menghitung persentase komposisi organik vs anorganik
- Memberi skor keyakinan (confidence) atas hasil analisis

## Latar Belakang Inisiasi

Proyek ini diinisiasi oleh **Daffa Jaya Perkasa** dari PT Makerindo Prima Solusi, atas kolaborasi dengan **Dr. Agus Mulyana, M.T.** (CEO PT Makerindo Prima Solusi, dosen D3 Teknik Komputer UNIKOM).

## Arsitektur Singkat

- **Model AI:** YOLOv8 (object detection), dilatih menggunakan Kaggle Notebook (GPU cloud)
- **Model Serving:** FastAPI (HTTP `/predict` + WebSocket `/ws/predict`)
- **Backend:** Node.js dengan pola Adapter (`IWasteAiAdapter`)
- **Frontend:** Dashboard monitoring performa AI & uji model
- **Dataset:** TACO (Trash Annotations in Context) + kurasi tambahan, lihat [`docs/dataset/`](docs/dataset/)

Detail lengkap arsitektur ada di [`docs/architecture/`](docs/architecture/).

## Struktur Direktori

```
berseka-ai/
├── data/               # Dataset (raw, processed, splits) — tidak di-commit penuh, lihat .gitignore
├── models/             # Checkpoint & model hasil training
├── notebooks/          # Kaggle/Jupyter notebooks untuk eksplorasi & training
├── src/
│   ├── training/       # Skrip training model
│   ├── preprocessing/  # Preprocessing & augmentasi dataset
│   ├── inference/       # Logika inference model
│   └── utils/          # Utilitas bersama
├── api/                # FastAPI model serving
│   ├── routes/
│   ├── schemas/
│   └── services/
├── web/                # Dashboard monitoring (frontend)
├── tests/              # Unit & integration tests
├── docs/               # Dokumentasi teknis (arsitektur, dataset, keputusan, API reference)
└── scripts/            # Skrip otomasi (training trigger, deployment, dll)
```

## Status Pengembangan

Lihat backlog & status QA per tahap secara lengkap di [`docs/BACKLOG.md`](docs/BACKLOG.md).

## Kontribusi

Proyek ini bersifat terbuka untuk pembelajaran dan pengembangan lanjutan. Lihat [`docs/architecture/`](docs/architecture/) sebelum berkontribusi.

## Lisensi

TBD

---

<sub>Diinisiasi & dikembangkan oleh <strong>Daffa Jaya Perkasa</strong> (<a href="https://github.com/dafayape">@dafayape</a>), PT Makerindo Prima Solusi, untuk Universitas Komputer Indonesia.</sub>
