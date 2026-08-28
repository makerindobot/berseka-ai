# BERSEKA Backend (Node.js) — Backlog 7

Backend integrasi antara Model Serving API (Backlog 6, FastAPI Python) dan
sistem monitoring KKN & tata kelola sampah, memakai **Adapter Pattern**
(`IWasteAiAdapter`) supaya business logic tidak bergantung langsung pada
detail implementasi model serving.

## Kenapa Adapter Pattern?

Backend TIDAK memanggil FastAPI langsung dari route handler. Semua akses ke
kapabilitas AI lewat `IWasteAiAdapter` (`src/adapters/IWasteAiAdapter.js`),
supaya:
1. Mudah di-mock untuk testing (`MockWasteAiAdapter`, tidak butuh FastAPI berjalan)
2. Mudah diganti implementasinya di masa depan (mis. gRPC, atau model
   in-process) tanpa mengubah route/business logic
3. Kontrak jelas satu tempat, bukan tersebar

> **Catatan penting:** interface `IWasteAiAdapter` di sini didesain oleh
> Dimas (Backend/ML Engineer) berdasarkan skema kontrak `/predict` yang
> SUDAH ada di Backlog 6 — belum ada dokumen interface terpisah dari Daffa
> yang ditemukan di repo. **Perlu review & sign-off Daffa** sebelum
> dianggap final, terutama penamaan method (`analyzeImage`, `healthCheck`)
> dan bentuk `WasteAiPredictionResult`.

## Instalasi

```bash
cd backend
npm install
cp .env.example .env   # sesuaikan WASTE_AI_API_BASE_URL, dll
```

## Menjalankan

Dengan Model Serving API FastAPI sungguhan (Backlog 6) berjalan di port 8000:

```bash
WASTE_AI_ADAPTER=fastapi WASTE_AI_API_BASE_URL=http://127.0.0.1:8000 npm start
```

Tanpa FastAPI (pakai mock adapter, untuk dev/test cepat):

```bash
WASTE_AI_ADAPTER=mock npm start
```

## Testing

```bash
npm test
```

15 test (`node --test`), cakupan: `ScanRepository` (CRUD & agregasi
compliance), `scanWindow` (logika jadwal pagi/sore), dan endpoint HTTP
penuh (`/api/scan`, `/api/scans`, `/api/scan/:id`, `/api/compliance/:id`,
`/healthz`) via `MockWasteAiAdapter` (tidak butuh proses eksternal apa pun,
cepat & deterministik untuk CI).

Diverifikasi juga END-TO-END sungguhan (bukan cuma mock): backend
`WASTE_AI_ADAPTER=fastapi` dijalankan bersama server FastAPI Backlog 6
nyata, dites via curl — chain penuh Backend → FastAPI → Mock AI → SQLite
→ response berjalan benar (lihat commit log Backlog 7 untuk detail).

## Struktur

```
backend/
├── src/
│   ├── adapters/
│   │   ├── IWasteAiAdapter.js         # Kontrak abstrak (Backlog 7)
│   │   ├── FastApiWasteAiAdapter.js   # Implementasi -> Model Serving API (Backlog 6)
│   │   ├── MockWasteAiAdapter.js      # Implementasi untuk testing backend
│   │   └── createWasteAiAdapter.js    # Factory berbasis env var
│   ├── db/
│   │   ├── schema.js                  # Skema SQLite (node:sqlite bawaan Node)
│   │   └── scanRepository.js          # Akses data histori scan
│   ├── lib/
│   │   └── scanWindow.js              # Logika jadwal scan pagi/sore
│   ├── routes/
│   │   └── scan.js                    # POST /api/scan, GET /api/scans, dll
│   └── server.js                      # Entry point Express
├── tests/                             # node --test
└── data/                              # SQLite db file (gitignored)
```

## Endpoint

| Method | Path | Deskripsi |
|---|---|---|
| GET | `/healthz` | Status backend + status model serving di baliknya |
| POST | `/api/scan?vendorId=&wargaId=&kelompokKknId=` | Analisis 1 foto (body: raw bytes gambar, Content-Type image/jpeg\|png\|webp) |
| GET | `/api/scan/:id` | Detail 1 hasil scan tersimpan |
| GET | `/api/scans?vendorId=&kelompokKknId=&limit=` | List histori scan |
| GET | `/api/compliance/:kelompokKknId` | Ringkasan kepatuhan (rata-rata organik%, jumlah scan valid) per kelompok KKN |

## Database

Pakai `node:sqlite` bawaan Node.js (stabil sejak Node 22.5) — sengaja
TIDAK memakai `better-sqlite3` (native addon, butuh compile toolchain) atau
Postgres/MySQL terpisah, karena skala proyek (32 kelompok KKN) & RAM
gateway (1.9GB, sudah dipakai monitoring Netdata) tidak butuh database
server terpisah.

Tabel `scans`: 1 baris per hasil scan (request_id, vendor_id, warga_id,
kelompok_kkn_id, scan_window, hasil AI ternormalisasi). Tabel
`scan_windows`: definisi jam pagi/sore (default 05:00-09:00 & 15:00-18:00,
**indikatif, perlu konfirmasi Daffa** untuk jam pasti program Coblong).

## Belum dikerjakan (transparan ke QC)

- `annotatedImageBase64` belum diupload ke object storage — saat ini hanya
  flag `stored_in_response_only` di DB (base64 penuh bisa besar, membebani
  RAM/disk gateway). Perlu integrasi storage (pola sama seperti
  `collector-bot/src/lib/storage.js`) di iterasi berikutnya.
- Autentikasi/otorisasi endpoint belum ada (siapa saja bisa POST /api/scan)
  — perlu didefinisikan sebelum deployment produksi (Backlog 11).
- Validasi `scan_windows` custom per klien/wilayah belum ada UI-nya
  (Backlog 8, dashboard).
