# BERSEKA AI — Rencana Pengumpulan Data Lapangan (32 Kelompok KKN Coblong)

**Status:** Tahap 1-3 selesai — pesan sudah dikirim ke Pak Agus & diteruskan ke 32 kelompok KKN. Sekarang tahap 4 (pengumpulan foto) sedang berlangsung.
**Diperbarui:** 28 Agustus 2026

---

## TAHAP 1 — Pesan ke Dr. Agus Mulyana (Ringkas, Sesuai Preferensi Beliau)

> Selamat pagi/siang, Pak Agus. Mohon maaf mengganggu waktu Bapak.
>
> Saya ingin memohon bantuan Bapak terkait proyek BERSEKA AI. Kami membutuhkan koordinasi ke seluruh 32 kelompok KKN di Kecamatan Coblong untuk membantu mengambil foto tong sampah sebagai data lapangan pelatihan model AI, karena ternyata belum ada dataset publik dengan sudut pandang seperti ini.
>
> Jika Bapak berkenan, saya akan kirimkan detail teknis dan panduan pengambilan fotonya menyusul. Mohon arahan Bapak mengenai waktu yang tepat untuk menyampaikan hal ini ke seluruh kelompok. Terima kasih banyak, Pak.
>
> Hormat saya,
> Daffa

**Catatan:** sesuaikan sapaan waktu (pagi/siang/sore) sebelum kirim.

**Status:** 🟢 SELESAI — sudah dikirim Daffa ke Pak Agus (28 Agustus 2026).

---

## TAHAP 2 — Pesan ke Mahasiswa (Setelah Pak Agus Setuju)

Berbeda dari pesan ke Pak Agus, pesan ini **harus detail dan jelas** karena mahasiswa yang akan mengeksekusi langkah teknisnya secara mandiri, kemungkinan tanpa pendampingan langsung.

> **📢 PENGUMPULAN DATA FOTO TONG SAMPAH — PROYEK BERSEKA AI**
>
> Halo teman-teman KKN Kecamatan Coblong! 👋
>
> Kelompok kalian diminta membantu mengumpulkan foto tong sampah untuk mendukung pengembangan sistem AI BERSEKA (Bersih, Sehat, Kampung Asri). Datanya akan dipakai melatih model AI yang nantinya dipakai warga Coblong sendiri — jadi kontribusi kalian di sini penting!
>
> **Cara Upload Foto (via Telegram, ±3 menit):**
> 1. Buka Telegram (kalau belum punya, install dulu dari Play Store/App Store — gratis).
> 2. Cari bot: **`@bersekabot`**, tekan **Start/Mulai**.
> 3. Ketik `/mulai`, lalu pilih nomor kelompok kalian dari daftar yang muncul (tinggal tap, tidak perlu ngetik).
> 4. Pilih jenis tong yang mau difoto: **Organik** atau **Anorganik** (tap tombolnya).
> 5. Foto tong sampah **dari ATAS** (tampak atas, tegak lurus), jarak sekitar 30-50 cm dari permukaan sampah, pastikan pencahayaan cukup dan tidak blur.
> 6. Kirim foto itu langsung di chat bot (seperti kirim foto biasa ke teman).
> 7. Tunggu bot balas centang ✅ — itu tandanya foto sudah tersimpan dengan benar.
> 8. Ulangi langkah 3-7 untuk tiap tong (boleh dari lokasi RT/RW berbeda di wilayah kalian, kondisi tong campuran: kosong/setengah/penuh).
>
> **🎯 Target:** minimal 10-15 foto per kelompok (campuran organik & anorganik), dikumpulkan sebelum **[tanggal deadline]**.
>
> **💡 Bonus:** dokumentasi ini bisa jadi bagian dari laporan kegiatan KKN kalian juga!
>
> Kalau bot error atau ada kendala, hubungi **[kontak koordinator]**.
>
> Terima kasih atas kontribusinya! 🙏

**Status:** 🟢 SELESAI — Pak Agus sudah meneruskan pesan ini ke 32 kelompok KKN.

---

## Mekanisme Teknis di Balik Layar (Untuk Tim, Bukan Dikirim ke Mahasiswa)

**Bot:** `@bersekabot` (bot Telegram baru, dibuat khusus untuk pengumpulan data lapangan — **terisolasi total dari Hermes Agent/gateway control**, murni relay foto→storage. Berbeda dari akun GitHub bot `makerindobot` yang dipakai untuk commit kode.)

- Bot berjalan sebagai proses terpisah (Node.js), tidak execute perintah apa pun ke sistem, tidak akses tools Hermes
- Wizard: `/mulai` → pilih kelompok (1-32) → pilih jenis tong → kirim foto → konfirmasi otomatis
- Foto langsung stream ke Cloudflare R2 (bukan disk gateway), path: `kelompok-{id}_rt{rt}-rw{rw}/{organik|anorganik}/{timestamp}.jpg`
- Metadata index tersimpan paralel (JSONL/Google Sheet)
- Sinkronisasi berkala ke Kaggle Dataset (1-2x sehari) untuk dipakai tim ML

**Estimasi implementasi:** 4-6 jam kerja, gratis (semua free tier).

---

## Status Keseluruhan

| Tahap | Status |
|-------|--------|
| 1. Kirim pesan ke Pak Agus | 🟢 SELESAI — Daffa sudah kirim (28 Agustus 2026) |
| 2. Bangun & deploy bot Telegram (isolated) | 🟢 SELESAI — `@bersekabot` live di gateway, storage mode `local` (sementara, belum R2), bug parsing ID kelompok sudah diperbaiki, bug polling EFATAL (IPv6) sudah diperbaiki 28 Agustus |
| 3. Kirim pesan ke mahasiswa | 🟢 SELESAI — Pak Agus sudah teruskan pesan ke 32 kelompok KKN |
| 4. Pengumpulan foto 32 kelompok | 🟡 BERLANGSUNG — **2 foto sudah masuk** per 28 Agustus 14:37 WIB (Kelompok 1 Sekeloa, Kelompok 11 Sadang Serang, keduanya jenis anorganik), diverifikasi langsung di `data-storage/manifest.jsonl` + file JPEG tersimpan (bukan cuma klaim UI). Masih jauh dari target minimal 10-15 foto/kelompok × 32 kelompok. |

**Catatan teknis penting:** bot sempat mengalami downtime fungsional (error `Polling error: EFATAL: AggregateError` berulang) dari sekitar 28 Agustus 11:28 WIB sampai diperbaiki ~14:31 WIB — periode ini kemungkinan ada foto yang GAGAL terkirim mahasiswa tanpa mereka sadari (bot tidak merespons). **Perlu follow-up ke koordinator/mahasiswa**: jika ada yang mencoba kirim foto di rentang waktu tersebut dan tidak dapat konfirmasi ✅, mohon kirim ulang.
