# BERSEKA AI — Image Quality Gate (Backlog 4)

| | |
|---|---|
| **Proyek** | BERSEKA AI — Sistem Monitoring Kepatuhan Pemilahan Sampah, Kec. Coblong (kerja sama UNIKOM) |
| **Modul** | `src/preprocessing/image_quality_check.py` |
| **Test** | `tests/unit/test_image_quality_check.py` (9 test, semua PASS) |
| **Disusun oleh** | Dimas — Backend/ML Engineer, Damaker Studio |
| **Status** | Modul & test lulus lokal. **Belum diintegrasikan ke endpoint `/predict`** (scope Backlog 6). |

---

## 1. Latar Belakang & Tujuan

Warga awam memfoto tong sampah pakai HP masing-masing tanpa panduan fotografi:
kamera bisa buram (tangan gemetar / gagal fokus), pencahayaan buruk (indoor
gelap, backlight, overexposed karena flash), atau resolusi sangat kecil
(kompresi berat aplikasi chat/WhatsApp). Jika foto semacam ini langsung masuk
ke model deteksi YOLOv8, hasil bounding box, klasifikasi organik/non-organik,
dan estimasi volume berisiko **ngawur** — bukan karena model salah, tapi
karena input di luar kemampuan model untuk dianalisis akurat.

Modul ini adalah **gate pre-inference**: memvalidasi kualitas foto SEBELUM
dikirim ke model, dan menolak dengan pesan jelas jika tidak layak, alih-alih
memaksakan inferensi pada gambar yang secara fundamental tidak informatif.

**Bukan scope modul ini:** integrasi ke endpoint `/predict` (HTTP) — itu
Backlog 6. Modul ini murni fungsi Python `check_image_quality()` yang siap
dipanggil dari endpoint tersebut nanti.

---

## 2. Tiga Pemeriksaan & Threshold

Urutan pengecekan: fail-fast dari yang termurah/paling fundamental terlebih
dahulu (resolusi → pencahayaan → blur), agar biaya komputasi Laplacian
(termahal) tidak selalu ditanggung untuk kasus yang sudah pasti gagal di
langkah lebih murah.

### 2.1 Resolusi — `MIN_SHORT_SIDE_PX = 320`, `MIN_TOTAL_PIXELS = 320×320`

**Alasan:** YOLOv8 pada umumnya di-training/infer pada input persegi 640×640
(default ultralytics). Sisi terpendek foto di bawah 320px berarti foto perlu
di-upscale >2x untuk mencapai resolusi input model — upscaling seperti ini
tidak menambah informasi asli, hanya menginterpolasi piksel, sehingga objek
kecil (misal butiran sampah, tutup botol) kehilangan detail tepi yang
dibutuhkan deteksi akurat. 320px dipilih sebagai **separuh** dari resolusi
input standar model — batas bawah yang masih realistis dicapai kamera HP
modern manapun (bahkan kamera VGA lama menghasilkan ≥640×480), sehingga
penolakan hanya terjadi pada kasus nyata: thumbnail, screenshot terkompresi,
atau crop ekstrem — bukan foto kamera normal.

### 2.2 Pencahayaan — `BRIGHTNESS_MIN = 40`, `BRIGHTNESS_MAX = 215`, `CLIPPED_PIXEL_RATIO_MAX = 0.55`

**Metode:** rata-rata brightness grayscale (skala 0–255) via histogram
`cv2.calcHist`, plus rasio piksel "clipped" (≤10 atau ≥245 — mendekati hitam/
putih murni, kehilangan detail warna).

**Alasan rentang 40–215 (dari skala penuh 0–255):**
- Di bawah 40: riset praktik computer vision umum menempatkan "foto gelap"
  di rentang mean brightness <40-50/255 sebagai ambang di mana detail warna
  & tepi objek mulai hilang ditelan noise sensor kamera HP (terutama kamera
  budget yang dipakai warga umum, ISO tinggi otomatis menambah noise di
  kondisi minim cahaya).
- Di atas 215: simetris secara desain — brightness mendekati 255 berarti
  sensor mulai jenuh (saturasi), detail highlight (tepi objek terang seperti
  kemasan plastik bening/logam mengkilap) hilang. Rentang tidak dibuat
  simetris 50/50 di titik 127.5 karena foto lapangan tampak-atas tong sampah
  (biasanya di luar ruangan/siang hari) secara alami cenderung sedikit lebih
  terang daripada gelap — memberi headroom lebih besar ke sisi terang (215
  vs 255, margin 40) dibanding proporsi margin di sisi gelap (40 vs 0)
  sengaja dibuat mirip agar simetris terhadap risiko clipping di kedua ujung.
- `CLIPPED_PIXEL_RATIO_MAX = 0.55`: pengecekan tambahan di luar rata-rata,
  untuk menangkap kasus **backlight** (sumber cahaya di belakang objek) —
  foto semacam ini bisa punya rata-rata brightness "normal" (karena separuh
  gambar sangat gelap, separuh sangat terang, saling menetralkan rata-rata)
  padahal informasi objek hilang total di kedua ekstrem. Ambang 55% dipilih
  konservatif (bukan 30-40%) agar foto dengan latar putih/langit terang wajar
  di sebagian frame (situasi umum foto luar ruangan) tidak salah ditolak.

### 2.3 Blur — `BLUR_VARIANCE_THRESHOLD = 100.0` (variansi Laplacian)

**Metode:** `cv2.Laplacian(gray, cv2.CV_64F).var()` — standar de-facto
komunitas OpenCV untuk deteksi blur (operator Laplacian menyorot tepi/edge;
gambar tajam punya edge kuat → variansi tinggi; gambar buram menghaluskan
edge → variansi mendekati 0).

**Verifikasi empiris yang dilakukan** (bukan hanya angka dari literatur):
dijalankan pada gambar sintetik yang dibuat dengan NumPy/OpenCV (bukan foto
asli, karena tidak ada sample foto lapangan tersedia saat modul ini dibuat):

| Skenario | Deskripsi | Variansi Laplacian |
|---|---|---|
| Tajam (noise acak + checkerboard, edge kuat) | simulasi foto fokus jelas + high-frequency detail | **~26.000** |
| Foto realistis tajam (bentuk warna-warni + teks) | simulasi foto tong sampah dgn banyak objek kecil | **~290–330** |
| Blur ringan (Gaussian kernel 3×3) | simulasi sedikit goyang tangan | **~20–55** |
| Blur sedang (Gaussian kernel 5×5–7×7) | simulasi fokus kurang tepat | **~2–10** |
| Blur berat (Gaussian kernel ≥9×9) | simulasi sangat buram/goyang parah | **~0.6–3** |
| Warna solid (blur ekstrem/tanpa tekstur) | kasus ekstrim, tanpa tepi sama sekali | **0.0** |

Hasil ini konsisten dengan rule-of-thumb yang umum dipakai komunitas
(threshold di kisaran 100 sering dikutip sebagai pembatas "blur vs tajam"
untuk foto natural resolusi menengah, misalnya artikel referensi PyImageSearch
"Blur detection with OpenCV"). **Gap besar** antara kelompok tajam (~290+)
dan kelompok blur bahkan ringan (~55 ke bawah) di eksperimen kami memberi
margin aman yang lebar untuk memilih 100 sebagai titik potong — cukup jauh
dari kedua kelompok sehingga toleran terhadap variasi tekstur foto nyata
(foto tajam tapi minim tekstur/background polos sekalipun tidak akan
serendah nilai blur ringan pada eksperimen di atas).

**Keterbatasan yang diketahui & mitigasi:** threshold ini divalidasi dengan
gambar SINTETIK (checkerboard/noise/teks buatan), bukan foto tong sampah asli
dari lapangan Kecamatan Coblong (foto lapangan asli belum tersedia — lihat
`dataset-decision.md` §7 poin 2). **Rekomendasi tindak lanjut**: begitu sesi
foto pilot lapangan (Backlog 3/held-out real-world set) tersedia, jalankan
ulang `check_image_quality()` pada sample foto tajam vs buram-sengaja dari
HP warga sungguhan, dan sesuaikan `BLUR_VARIANCE_THRESHOLD` bila perlu — nilai
100 di sini adalah estimasi awal yang defensible secara teknis (didukung
eksperimen numerik + rujukan praktik umum), bukan angka final yang sudah
divalidasi terhadap data lapangan produksi.

---

## 3. Kontrak Return Value

```python
{
    "valid": bool,
    "reason": str | None,        # None jika valid; pesan human-readable (Bahasa Indonesia) jika ditolak
    "metrics": {
        "blur_score": float,             # variansi Laplacian
        "brightness_score": float,       # rata-rata grayscale 0-255
        "clipped_pixel_ratio": float,    # 0.0-1.0
        "resolution": {"width": int, "height": int},
    },
}
```

Semua threshold dapat di-override lewat parameter fungsi (untuk keperluan
testing/tuning), namun nilai default di modul adalah SATU sumber kebenaran
konfigurasi produksi — jangan hardcode ulang di tempat lain (konsisten dengan
konvensi proyek seperti `configs/label_mapping.yaml`).

---

## 4. Status Verifikasi

- ✅ Modul `image_quality_check.py` diimplementasikan sesuai kontrak.
- ✅ 9 unit test di `tests/unit/test_image_quality_check.py` dijalankan via
  `pytest` — **semua PASS** (gambar sintetik: solid color, blur berat, tajam,
  gelap, overexposed, resolusi rendah, kondisi valid, skema return value,
  input invalid).
- ✅ Threshold blur diverifikasi empiris dengan eksperimen numerik terpisah
  (lihat §2.3), bukan hanya diasumsikan dari literatur.
- ❌ **Belum** diverifikasi terhadap foto tong sampah ASLI dari lapangan
  (belum ada data lapangan Coblong tersedia saat modul ini dibuat — lihat
  `dataset-decision.md` §7).
- ❌ **Belum** diintegrasikan ke endpoint `/predict` (scope Backlog 6, di luar
  tugas modul ini secara eksplisit).

**Kesimpulan jujur:** modul ini defensible secara teknis untuk gate awal
produksi (logika benar, threshold berdasar riset + eksperimen, test lulus),
tapi threshold — khususnya blur — sebaiknya dikalibrasi ulang begitu foto
lapangan asli tersedia, sebelum dianggap final untuk audit klien.
