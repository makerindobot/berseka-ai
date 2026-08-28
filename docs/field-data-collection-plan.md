# BERSEKA AI — Rencana Pengumpulan Data Lapangan (32 Kelompok KKN Coblong)

**Status:** Draft — menunggu persetujuan & eksekusi Daffa
**Dibuat:** 28 Agustus 2026

---

## 1. Pesan WhatsApp ke Dr. Agus Mulyana

### Versi Ringkas (basa-basi awal)

> Selamat pagi/siang, Pak Agus. Mohon maaf mengganggu waktu Bapak.
>
> Saya ingin memohon bantuan Bapak terkait proyek BERSEKA AI. Kami membutuhkan koordinasi ke seluruh 32 kelompok KKN di Kecamatan Coblong untuk membantu mengambil foto tong sampah sebagai data lapangan pelatihan model AI, karena ternyata belum ada dataset publik dengan sudut pandang seperti ini.
>
> Jika Bapak berkenan, saya akan kirimkan detail teknis dan panduan pengambilan fotonya menyusul. Mohon arahan Bapak mengenai waktu yang tepat untuk menyampaikan hal ini ke seluruh kelompok. Terima kasih banyak, Pak.
>
> Hormat saya,
> Daffa

### Versi Lengkap (pesan detail)

> Selamat pagi/siang, Pak Agus. Mohon maaf mengganggu waktu Bapak.
>
> Saya ingin melaporkan perkembangan proyek BERSEKA AI (sistem AI monitoring kepatuhan pemilahan sampah untuk Kecamatan Coblong). Dari sisi riset teknis, kami menemukan bahwa saat ini belum ada dataset publik yang menyediakan foto tong sampah dengan sudut pandang tampak atas. Oleh karena itu, data asli dari lapangan Coblong menjadi sangat krusial agar model AI yang kami bangun benar-benar akurat di dunia nyata, bukan sekadar demo.
>
> Mengingat hal tersebut, saya ingin memohon bantuan Bapak untuk mengoordinasikan seluruh 32 kelompok KKN di Kecamatan Coblong agar mahasiswa dapat membantu mengambil foto tong sampah sebagai data lapangan. Berikut ringkasan kebutuhan teknisnya:
>
> 1. Foto diambil tampak atas (dari atas, tegak lurus) pada tong sampah organik dan anorganik secara terpisah.
> 2. Jarak kamera sekitar 30-50 cm dari permukaan sampah, agar hasil foto konsisten.
> 3. Diambil dalam berbagai kondisi: pencahayaan berbeda (siang, sore, dalam ruangan), berbagai tingkat isi tong (kosong, setengah, penuh), serta berbagai kondisi sampah.
> 4. Total target sekitar 300-500 foto dari seluruh 32 kelompok, sehingga cukup jika masing-masing kelompok mengambil sekitar 10-15 foto saja.
> 5. Setiap foto mohon diberi keterangan sederhana saat pengambilan: jenis tong (organik/anorganik), lokasi RT/RW, dan waktu pengambilan.
>
> Kami juga berharap kegiatan ini bisa menjadi nilai tambah bagi mahasiswa, karena dokumentasi dan data yang mereka kumpulkan dapat dimasukkan sebagai bagian dari laporan kegiatan KKN mereka, sehingga tidak hanya menjadi tugas tambahan tanpa manfaat.
>
> Jika Bapak berkenan, saya siap menyiapkan panduan teknis singkat (semacam petunjuk pengambilan foto) yang bisa dibagikan ke seluruh kelompok, termasuk ke Kelompok 1 di Sadang Serang yang kebetulan Bapak dampingi langsung. Mohon arahan Bapak mengenai waktu dan cara terbaik untuk menyampaikan hal ini ke seluruh kelompok KKN, apakah melalui grup koordinator, rapat DPL, atau jalur lain yang biasa digunakan.
>
> Mohon maaf jika pesan ini cukup panjang, Pak. Terima kasih banyak atas waktu dan bantuannya. Saya tunggu arahan Bapak.
>
> Hormat saya,
> Daffa

**Catatan:** sesuaikan sapaan waktu (pagi/siang/sore) sebelum kirim.

---

## 2. Mekanisme Teknis Pengumpulan Foto

**Rekomendasi:** Bot Telegram sederhana, di-host di gateway (ringan, tidak butuh GPU), foto disimpan ke Cloudflare R2 (bukan disk gateway), metadata tercatat otomatis via wizard interaktif.

### Alasan
- Zero/minimal-install untuk mahasiswa (Telegram sudah lazim dipakai)
- Metadata (kelompok, RT/RW, jenis tong, waktu) terekam otomatis via tombol, bukan input manual rawan typo
- Bisa live dalam hitungan jam, cocok untuk deadline ketat
- Foto langsung terstruktur siap pakai untuk pipeline ML, tanpa proses ekspor manual

### Langkah Implementasi
1. **Setup bot** (30-60 menit) — buat via @BotFather, folder `berseka-ai/collector-bot` (Node.js, pola Adapter)
2. **Desain flow wizard** (1-2 jam) — `/mulai` → pilih kelompok (1-32) → pilih jenis tong (Organik/Anorganik) → kirim foto → bot balas konfirmasi otomatis
3. **Penyimpanan terstruktur** (1-2 jam) — foto langsung stream ke Cloudflare R2 dengan path `kelompok-{id}_rt{rt}-rw{rw}/{organik|anorganik}/{timestamp}.jpg`, metadata index di JSONL/Google Sheet
4. **Sinkronisasi ke Kaggle** (30-60 menit setup) — script pull dari R2 → upload sebagai Kaggle Dataset via API, dijalankan 1-2x sehari

**Estimasi waktu total implementasi:** 4-6 jam kerja fokus, bisa live di hari yang sama
**Biaya:** Rp0 (semua free tier — Telegram Bot API, Cloudflare R2, Kaggle API)

### Instruksi untuk Mahasiswa KKN

> **CARA UPLOAD FOTO TONG SAMPAH (via Telegram, 3 menit):**
> 1. Buka Telegram (kalau belum punya, install dari Play Store/App Store — gratis).
> 2. Cari bot: `@BERSEKA_collector_bot` (link dibagikan panitia), tekan Start/Mulai.
> 3. Ketik `/mulai`, pilih nomor kelompok kalian dari daftar (tap tombol, tidak perlu ngetik).
> 4. Pilih jenis tong: Organik atau Anorganik (tap tombol).
> 5. Foto tong sampah dari ATAS (pastikan pencahayaan cukup, tidak blur), kirim foto seperti biasa.
> 6. Tunggu bot balas centang ✅ — tanda foto tersimpan dengan benar.
> 7. Ulangi untuk tiap tong (boleh dari RT/RW berbeda di wilayah kalian).
> 8. **Target:** minimal 10-15 foto per kelompok, dikumpulkan sebelum [deadline ditentukan panitia].
>
> Kalau bot error, hubungi [kontak koordinator] untuk alternatif Google Form.

---

## Rencana Selanjutnya
1. Daffa mengirim pesan ke Dr. Agus Mulyana (pilih versi ringkas/lengkap)
2. Setelah dapat lampu hijau & timeline dari Pak Agus, Bayu mulai implementasi bot Telegram (paralel dengan Backlog 2 training pipeline)
3. Bot live → distribusikan instruksi ke 32 kelompok → foto masuk bertahap → sync ke Kaggle Dataset
