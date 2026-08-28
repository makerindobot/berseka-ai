# Kalibrasi Kamera & Panduan Foto — BERSEKA AI

**Backlog:** 3 — Kalibrasi Kamera & Validasi Estimasi Volume
**Penulis:** Nara (UI/UX Designer, Damaker Studio)
**Status dokumen:** 🟡 **VERSI 1 — TEORITIS/RISET**, belum divalidasi dengan foto lapangan asli
**Tanggal:** 28 Agustus 2026

---

## ⚠️ Status & Disclaimer Penting

Dokumen ini adalah **dasar teknis konseptual** yang disusun dari riset spesifikasi kamera HP umum, standar ukuran tong sampah rumah tangga Indonesia, dan perhitungan geometri optik (field of view). Dokumen ini **BUKAN hasil akhir** dan **BELUM boleh dipakai di produksi** sebelum divalidasi dengan data foto nyata dari bot Telegram (warga Kecamatan Coblong).

Semua angka di bawah — rentang jarak, formula penalty, dan tabel kalibrasi volume — ditandai sesuai status validasinya:

- 🟢 **Berbasis riset/sumber terverifikasi** (spesifikasi kamera, standar ukuran tong)
- 🟡 **Turunan matematis dari asumsi riset** (perlu dicek ulang dengan sampel nyata)
- 🔴 **WAJIB DIVALIDASI dengan foto lapangan Coblong** sebelum dipakai sebagai acuan produksi (lihat bagian [Rencana Validasi](#7-rencana-validasi-dengan-data-lapangan-coblong))

Referensi QC 3 (Sari): *"Uji dengan sample foto pada jarak bervariasi, verifikasi estimasi volume konsisten dalam toleransi wajar (%error terdokumentasi)"* — pengujian ini baru bisa dilakukan setelah data lapangan tersedia.

---

## 1. Riset Dasar

### 1.1 Spesifikasi kamera HP umum

Sumber: Android Authority, Engadget, dan analisis lensa smartphone flagship/mid-range 2023–2024.

| Jenis lensa | Field of View (FOV) diagonal | Catatan |
|---|---|---|
| Kamera utama (wide, 1x, ~24-26mm ekuivalen) | ~78°–85° | Lensa **default** kamera HP saat dibuka pertama kali |
| Ultra-wide (0.5x) | ~110°–120° | Distorsi lengkung kuat di tepi frame — **tidak disarankan** untuk deteksi objek |
| Telephoto (2x-5x) | Lebih sempit, bervariasi | Tidak relevan untuk kasus ini |

**Keputusan desain:** BERSEKA AI **mewajibkan penggunaan kamera utama (1x/wide, BUKAN ultrawide)** karena distorsi lensa ultra-wide di tepi frame akan merusak akurasi bounding box dan estimasi ukuran objek sampah kecil.

Karena FOV yang biasa dipublikasikan adalah **FOV diagonal**, sedangkan foto umumnya beraspek rasio 4:3 (potret), **FOV horizontal efektif lebih sempit** dari angka diagonal — untuk foto potret tampak-atas, dimensi terpendek frame (lebar) adalah faktor pembatas apakah tong sampah muat penuh.

Untuk perhitungan konservatif (aman, tidak mengasumsikan kamera terlalu premium), dokumen ini memakai:

> **FOV efektif (horizontal, dimensi pembatas) = 65°** (nilai tengah realistis, di antara 60°–70° yang lazim untuk sisi pendek frame kamera utama HP kelas menengah-atas)

🔴 **Perlu divalidasi**: nilai FOV efektif 65° adalah estimasi konservatif dari data publik, bukan hasil pengukuran pada HP yang benar-benar dipakai warga Coblong. Sebaiknya dikonfirmasi dengan minimal 3-5 model HP populer di Indonesia (misal via app kamera bawaan + cek metadata EXIF foto asli yang masuk).

### 1.2 Ukuran tong sampah rumah tangga Indonesia (10L–50L)

Sumber: Monotaro Indonesia (panduan tempat sampah), referensi produk tempat sampah 37.85L/60L, dan SNI 3242-2008 (Tata Cara Pengelolaan Sampah Permukiman).

Kategori umum: tong sampah dapur/rumah tangga tipikal **10L–50L** (di luar tong komunal outdoor 120L+).

Karena bentuk tong bervariasi (silinder, kotak, ember), dokumen ini memodelkan tong sebagai **silinder dengan rasio tinggi:diameter ≈ 1.1:1** (mendekati bentuk ember/tong rumah tangga umum berdasarkan data produk 60L: 47×57×57cm). Dari rumus volume silinder:

```
V = π × (D/2)² × H,  dengan H ≈ 1.1 × D
→ D = ( 4V / (1.1 × π) )^(1/3)
```

| Volume tong | Estimasi diameter bukaan atas | Estimasi tinggi |
|---|---|---|
| 10 L | ~22 cm | ~24 cm |
| 20 L | ~28 cm | ~31 cm |
| 30 L | ~33 cm | ~36 cm |
| 40 L | ~36 cm | ~40 cm |
| 50 L | ~39 cm | ~43 cm |

🟡 **Asumsi turunan**: rasio 1.1:1 adalah pendekatan umum, bentuk tong asli warga Coblong bisa lebih pendek/gemuk (mis. ember cat bekas) atau lebih tinggi/langsing (tong plastik standar). 🔴 **Perlu difoto & diukur manual minimal 10-15 sampel tong nyata dari Coblong** untuk mengoreksi rasio ini.

---

## 2. Rentang Jarak Kamera Optimal (Tampak Atas)

### 2.1 Reasoning matematis

Lebar area yang tertangkap kamera pada jarak `d` dari objek:

```
capture_width(d) = 2 × d × tan(FOV/2)
```

Dengan FOV efektif = 65° → tan(32.5°) ≈ 0.6371 → `capture_width(d) ≈ 1.274 × d`

Agar tong sampah **masuk penuh dalam frame** namun **cukup besar untuk deteksi objek kecil di dalamnya** (mis. puntung rokok, bungkus kecil), area tong sebaiknya mengisi **40%–70% dari lebar frame** (fill ratio):

- Fill ratio > 70% → risiko tong terpotong di tepi frame (foto terlalu dekat)
- Fill ratio < 40% → tong terlalu kecil di frame, detail objek sampah kecil hilang/di bawah resolusi minimum deteksi (foto terlalu jauh)

Rumus jarak untuk fill ratio target `r`:

```
d = D_tong / (2 × tan(FOV/2) × r) = D_tong / (1.274 × r)
```

### 2.2 Hasil perhitungan per ukuran tong

| Volume tong | Diameter (cm) | Jarak (fill 70%, batas dekat) | Jarak (fill 40%, batas jauh) |
|---|---|---|---|
| 10 L | 22 | ~25 cm | ~43 cm |
| 20 L | 28 | ~31 cm | ~55 cm |
| 30 L | 33 | ~37 cm | ~65 cm |
| 40 L | 36 | ~40 cm | ~71 cm |
| 50 L | 39 | ~44 cm | ~77 cm |

### 2.3 Rekomendasi rentang jarak — **jawaban untuk arahan Daffa**

Karena aplikasi butuh **satu instruksi sederhana** untuk semua warga (bukan formula berbeda per ukuran tong), diambil irisan yang paling relevan untuk mayoritas tong rumah tangga (10L–30L, kategori paling umum untuk dapur/kamar sesuai riset 1.2):

> ## 📏 **Rentang jarak optimal: 30 cm – 50 cm dari permukaan atas tong sampah, tampak atas (top-down) tegak lurus**

- Tong kecil (10-20L): idealnya di ujung dekat rentang (30-40cm)
- Tong sedang-besar (30-50L): idealnya di ujung jauh rentang (40-50cm), atau maksimal hingga 60cm untuk tong 50L agar tidak terpotong

Jarak **< 25cm** dianggap **terlalu dekat** (risiko tong terpotong / blur fokus makro pada sebagian HP). Jarak **> 70cm** dianggap **terlalu jauh** (detail sampah kecil hilang, resolusi efektif per objek turun signifikan).

🔴 **WAJIB DIVALIDASI**: angka 30-50cm ini adalah hasil kalkulasi geometris teoritis. Begitu foto lapangan Coblong masuk, harus dicek: (a) apakah warga secara natural memfoto di rentang ini, (b) apakah model deteksi memang paling akurat di rentang ini secara empiris — sesuai instruksi QC 3 Sari.

---

## 3. Aturan Penalty Kualitas (Confidence Adjustment)

### 3.1 Prinsip

Sistem menghitung **rasio area** bounding box tong sampah (atau area sampah terdeteksi) terhadap total area frame foto:

```
area_ratio = luas_bbox_px / luas_total_frame_px
```

Ini adalah proxy langsung untuk "seberapa dekat/jauh jarak pengambilan foto dari rentang optimal", tanpa perlu sensor jarak tambahan.

Dari perhitungan Bagian 2 (fill ratio 40%-70% linear → area ratio adalah kuadrat dari fill ratio karena objek 2D):

```
area_ratio_min (optimal, batas jauh) ≈ 0.40² = 0.16 (16%)
area_ratio_max (optimal, batas dekat) ≈ 0.70² = 0.49 (49%)
```

Dibulatkan untuk toleransi praktis: **rentang optimal area_ratio = 15%–50%**

### 3.2 Formula multiplier confidence

```python
def quality_multiplier(area_ratio: float, bbox_touches_edge: bool) -> float:
    # Hard block: bbox tersentuh >= 2 sisi frame -> objek kemungkinan terpotong
    if bbox_touches_edge:
        return 0.0  # tolak / minta foto ulang, jangan proses estimasi volume

    r_min, r_max = 0.15, 0.50

    if r_min <= area_ratio <= r_max:
        return 1.0  # optimal, tidak ada penalty

    if area_ratio < r_min:
        # terlalu jauh -> menurun linear menuju floor 0.3 saat area_ratio -> 0
        return max(0.3, area_ratio / r_min)

    # area_ratio > r_max -> terlalu dekat, menurun linear menuju floor 0.3 saat area_ratio -> 1.0
    return max(0.3, 1 - (area_ratio - r_max) / (1 - r_max) * 0.7)

final_confidence = raw_model_confidence * quality_multiplier(area_ratio, bbox_touches_edge)
```

### 3.3 Aturan tampilan ke pengguna

| Kondisi | multiplier | Label UI | Aksi |
|---|---|---|---|
| `bbox_touches_edge = True` | 0.0 | **"Tong sampah terpotong"** | Blokir hasil, wajib foto ulang |
| `area_ratio` di [0.15, 0.50] | 1.0 | (tidak ada label) | Proses normal |
| `area_ratio` di [0.05, 0.15) atau (0.50, 0.70] | 0.5–1.0 | **"Kualitas sedang"** | Tampilkan hasil + saran "dekatkan/jauhkan kamera" |
| `area_ratio` < 0.05 atau > 0.70 | < 0.5 (floor 0.3) | **"Kualitas rendah"** | Tampilkan hasil dengan warning jelas, sarankan foto ulang |

Ini menjawab arahan Daffa poin 2: *"jika asal (foto sembarangan) = potensi hasil/kualitasnya rendah"* — foto asal-asalan akan otomatis mendapat area_ratio di luar rentang optimal (baik karena user menjauh untuk "ambil cepat" atau terlalu dekat/miring), sehingga confidence-nya turun otomatis dan sistem menandainya, bukan menyembunyikan ketidakpastian.

🟡 Threshold 15%/50% dan floor 0.3 adalah nilai **awal yang masuk akal secara matematis**, bukan hasil tuning empiris. 🔴 **Perlu dikalibrasi ulang** begitu tersedia data label manual vs confidence model pada foto nyata (mis. cari threshold yang memaksimalkan korelasi area_ratio terhadap %error volume aktual).

---

## 4. Tabel Kalibrasi Awal: Area Piksel Bounding Box → Estimasi Volume

### 4.1 Asumsi dasar

Karena foto adalah proyeksi 2D (top-down) dan tidak ada sensor kedalaman, volume tidak bisa dihitung langsung dari luas piksel — perlu **asumsi jarak referensi tetap** agar skala piksel↔cm konsisten. Sistem **mengunci jarak referensi kalibrasi di titik tengah rentang optimal: 40 cm**, dan asumsi resolusi foto standar **4000 × 3000 px (12MP, rasio 4:3)** — resolusi umum HP kelas menengah ke atas di Indonesia.

Skala piksel per cm pada jarak referensi 40cm:

```
capture_width(40cm) = 1.274 × 40 = ~51 cm (lebar dunia nyata tertangkap di frame)
px_per_cm = lebar_frame_px / capture_width_cm = 4000 / 51 ≈ 78.4 px/cm
```

Diameter tong dalam piksel = `D_tong_cm × 78.4`. Bounding box (perkiraan kotak pembungkus lingkaran) = `diameter_px²`.

Karena `Area_px ∝ D²` dan `Volume ∝ D³` (Bagian 1.2), maka:

```
Volume ≈ k × Area_px^1.5
```

Dengan `k` dikalibrasi dari titik data 30L (nilai tengah): **k ≈ 1.73 × 10⁻⁹**

### 4.2 Tabel kalibrasi v1

| Volume tong | Diameter (cm) | Diameter (px, @40cm, 4000×3000) | Area bbox (px²) | Formula cek (k×Area^1.5) |
|---|---|---|---|---|
| 10 L | 22 | ~1.725 | ~2.98 juta | ~8.9 L |
| 20 L | 28 | ~2.196 | ~4.82 juta | ~20.3 L |
| 30 L | 33 | ~2.588 | ~6.70 juta | ~30.0 L (titik kalibrasi) |
| 40 L | 36 | ~2.823 | ~7.97 juta | ~38.9 L |
| 50 L | 39 | ~3.058 | ~9.35 juta | ~49.5 L |

**Formula produksi (v1, sementara):**

```
estimated_volume_liter = 1.73e-9 × (bbox_area_px)^1.5
```

Catatan implementasi:
- Formula ini HANYA valid untuk foto yang diambil pada jarak referensi ~40cm dengan resolusi ~4000×3000px. Untuk resolusi HP berbeda, `bbox_area_px` harus dinormalisasi dulu ke skala 4000×3000 (kalikan rasio resolusi).
- Karena rentang optimal adalah 30-50cm (bukan titik tetap 40cm), ada margin error sistematis ±20-25% pada estimasi volume dari efek jarak saja — di luar error deteksi model. Idealnya, versi produksi (v2) memakai jarak aktual (jika tersedia dari data sensor/EXIF/estimasi skala objek referensi) untuk normalisasi, bukan asumsi jarak tetap.

🔴 **WAJIB DIVALIDASI dengan Coblong**: tabel ini murni turunan geometri + asumsi bentuk silinder generik. Validasi yang dibutuhkan:
1. Ambil foto real 10-15 tong dengan volume terukur manual (isi air/pasir + gelas ukur, atau ukur dimensi fisik langsung)
2. Bandingkan `bbox_area_px` hasil deteksi model vs `estimated_volume_liter` formula vs volume aktual terukur
3. Hitung %error, sesuai instruksi QC 3 Sari — jika error > toleransi wajar (disarankan target awal ±15-20%), kalibrasi ulang konstanta `k` atau ganti model regresi (mungkin perlu non-cylinder assumption / regresi linear sederhana dari data nyata alih-alih rumus geometri murni)

---

## 5. Panduan Foto untuk Warga (Bahasa Indonesia Awam)

*Teks & ilustrasi deskriptif ini untuk dipakai di layar kamera aplikasi (Backlog 7/8 — UX submission foto).*

### 📸 Cara Foto Tong Sampah yang Benar

**1. Posisi HP: Tegak lurus dari atas**
> Bayangkan Anda mau foto isi tong sampah seperti foto makanan di atas meja — pegang HP **sejajar dengan tanah, layar menghadap lurus ke bawah** ke arah tong sampah. Jangan miring ke samping, jangan foto dari sudut serong.

*(Ilustrasi teks: gambar siluet orang berdiri di samping tong sampah terbuka, tangan memegang HP lurus di atas tong dengan garis putus-putus vertikal dari HP ke tengah tong, membentuk sudut 90° dengan permukaan sampah)*

**2. Jarak: Sekitar 1 telapak tangan + 1 lengan bawah dari tong (± 30-50 cm)**
> Kira-kira: rentangkan tangan Anda dari siku ke ujung jari, tambah sedikit lagi — itu jarak yang pas antara HP dan permukaan sampah. Jangan terlalu dekat (tong jadi kepotong di layar), jangan terlalu jauh (sampah kecil jadi tidak kelihatan jelas).

*(Ilustrasi teks: dua gambar perbandingan — kiri "❌ Terlalu dekat" menunjukkan tong yang gambarnya terpotong di tepi layar; kanan "❌ Terlalu jauh" menunjukkan tong kecil di tengah layar kosong; tengah "✅ Pas" menunjukkan tong mengisi sebagian besar layar dengan sedikit ruang kosong di pinggir)*

**3. Pastikan seluruh mulut tong masuk dalam kotak foto**
> Sebelum menekan tombol foto, cek di layar: apakah **seluruh lingkaran/kotak bagian atas tong terlihat utuh**, tidak ada bagian yang terpotong di tepi layar?

**4. Buka tutup tong (jika ada) dan pastikan pencahayaan cukup**
> Foto di tempat terang (siang hari atau lampu menyala). Hindari foto di tempat gelap atau membelakangi cahaya matahari langsung (bayangan HP/badan menutupi sampah).

**5. Tahan HP diam sesaat sebelum menekan tombol**
> Foto yang buram/goyang akan sulit dibaca sistem. Tahan napas sebentar, pastikan gambar tidak kabur sebelum menekan tombol foto.

**6. Gunakan kamera utama (1x), jangan mode "wide"/"0.5x"**
> Kalau HP Anda punya beberapa pilihan lensa di layar kamera (biasanya tombol angka seperti 0.5x, 1x, 2x), pastikan memilih **1x** (kamera normal), bukan 0.5x (lensa super lebar) — supaya bentuk tong tidak melengkung aneh di foto.

### Ringkasan cepat (untuk tooltip singkat di app):

> **✅ Tips foto:** Pegang HP lurus di atas tong (90°) • Jarak ±30-50cm (sepanjang lengan bawah) • Pastikan seluruh tong masuk frame • Tempat terang • Kamera 1x, bukan wide

---

## 6. Ringkasan Jawaban untuk Arahan Daffa

| Arahan Daffa | Jawaban di dokumen ini |
|---|---|
| "Validasi bacaan kamera+AI vs manual" | Bagian 7 — rencana validasi dengan data lapangan Coblong (belum bisa dieksekusi, tunggu data bot Telegram) |
| "Jarak & posisi kamera optimal jadi acuan aplikasi" | Bagian 2 — **30-50cm, tampak atas tegak lurus (top-down)**, dengan reasoning matematis FOV vs jarak vs area tertangkap |
| "Foto asal-asalan = kualitas rendah" | Bagian 3 — formula `quality_multiplier` berbasis `area_ratio` bbox, otomatis menurunkan confidence & memberi label kualitas |

---

## 7. Rencana Validasi dengan Data Lapangan Coblong

Setelah bot Telegram mulai mengumpulkan foto warga, langkah validasi wajib (before produksi):

1. **Ukur manual** dimensi & volume 10-15 tong sampah nyata yang dipakai warga Coblong (bandingkan dengan asumsi Bagian 1.2)
2. **Cek metadata EXIF** foto masuk (jika tersedia) untuk memperkirakan jarak/FOV kamera HP yang benar-benar dipakai warga, bandingkan dengan asumsi FOV 65° (Bagian 1.1)
3. **Plot distribusi** jarak foto natural warga (tanpa diarahkan) vs jarak yang disarankan panduan — cek apakah instruksi di Bagian 5 realistis diikuti
4. **Hitung %error** estimasi volume formula (Bagian 4.2) vs volume aktual terukur pada foto-foto tersebut
5. **Re-kalibrasi** konstanta `k`, threshold `area_ratio`, dan rentang jarak jika %error di luar toleransi (target awal ±15-20%, dikonfirmasi ke Daffa)
6. Update dokumen ini menjadi **v2** dengan tag jelas data mana yang sudah tervalidasi

**Tidak boleh melewati langkah ini sebelum Backlog 3 ditandai 🟢 selesai lolos QC 3 (Sari).**
