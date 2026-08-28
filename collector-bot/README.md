# BERSEKA Collector Bot

Bot Telegram untuk mengumpulkan foto tong sampah dari 32 kelompok mahasiswa
KKN di Kecamatan Coblong, sebagai data lapangan untuk proyek **BERSEKA AI**.

Nama bot Telegram: **`@bersekabot`** — ini bot Telegram **BARU**, dibuat
dari nol via @BotFather khusus untuk keperluan ini. Bukan reuse token/akses
dari sistem lain (termasuk bukan akun GitHub bot `makerindobot` yang sudah
ada — itu konteks berbeda; nama sempat salah ditulis `@makerindobot` di
draf awal dokumen ini, sudah dikoreksi 28 Agustus 2026).

---

## Status Deployment (Live)

Bot **sudah aktif** di gateway sejak 28 Agustus 2026, berjalan sebagai `berseka-collector-bot.service`.

**Catatan perubahan dari desain awal (ditemukan saat deployment):**
- Runtime dipindah dari `/home/maker/.../collector-bot` ke **`/opt/berseka-collector-bot`**. Sebab: `ProtectHome=true` di systemd menyembunyikan seluruh `/home` dari proses sandboxed, sehingga user `berseka-bot` tidak bisa `chdir` ke folder manapun di bawah `/home` meski ACL diberikan. Menaruh runtime di `/opt/` (di luar `/home`) adalah pola standar untuk service Linux dan menjaga `ProtectHome=true` tetap aktif penuh tanpa pengecualian.
- Opsi `MemoryDenyWriteExecute=true` **dihapus** dari service file. Sebab: V8 (mesin JS Node.js) butuh JIT compilation yang menulis+mengeksekusi memori secara dinamis — opsi ini menyebabkan core dump (`SIGTRAP`) setiap kali Node mencoba compile kode. Ini trade-off yang diketahui untuk runtime dengan JIT (Node/V8, Java, dll); seluruh proteksi sandboxing lain (`ProtectSystem=strict`, `NoNewPrivileges`, `CapabilityBoundingSet=` kosong, dll) tetap aktif.
- Source code kanonis tetap di repo Git ini (`collector-bot/`); folder `/opt/berseka-collector-bot` adalah *deployment copy*. **Update 28 Agustus 2026: skrip sync otomatis sudah dibuat** (`collector-bot/deploy.sh`, `sudo bash collector-bot/deploy.sh`) — menggantikan `sudo cp -r` manual yang sebelumnya jadi gap dokumentasi (risiko drift diam-diam antara source & runtime kalau lupa sync). **WAJIB jalankan skrip ini setiap ada perubahan kode di `collector-bot/`**, jangan edit `/opt/berseka-collector-bot` langsung.
- **Bug ditemukan & diperbaiki 28 Agustus 2026: `Polling error: EFATAL: AggregateError` berulang.** Root cause: VPS ini punya AAAA record (IPv6) yang di-resolve tapi network IPv6-nya *unreachable* (provider tidak route IPv6 dengan benar), dikombinasikan dengan Node.js v22+ yang defaultnya mengaktifkan `autoSelectFamily` (algoritma Happy Eyeballs — mencoba IPv6 & IPv4 bersamaan). Setiap request ke Telegram API mencoba IPv6 dulu, gagal, di-retry ke IPv4, dan kegagalan IPv6 yang berulang kadang dibungkus jadi `AggregateError` yang bocor ke `polling_error` handler. **BUKAN bug di kode bot** (`bot.js` tidak diubah) — diperbaiki di level systemd unit dengan menambahkan `Environment=NODE_OPTIONS=--dns-result-order=ipv4first --no-network-family-autoselection` ke `/etc/systemd/system/berseka-collector-bot.service`, memaksa Node.js selalu pakai IPv4 langsung tanpa race ke IPv6. Diverifikasi stabil (0 error) selama pemantauan langsung >3 menit setelah fix.

## Security & Isolation (baca ini dulu)

Bot ini **SENGAJA didesain terisolasi total** dari Claude Code (asisten AI
yang mengerjakan proyek ini) dan dari VPS gateway control plane
(`hermes-gateway`/`9router.service`). Ini keputusan keamanan eksplisit dari
pemilik proyek (Daffa), bukan kebetulan arsitektur. Catatan ini untuk
referensi audit keamanan di masa depan.

**Kenapa:** mahasiswa yang mengirim command/foto ke bot ini tidak boleh, baik
langsung maupun tidak langsung, bisa mengakses atau berinteraksi dengan
Claude Code atau sistem kontrol gateway VPS.

**Bagaimana isolasi ini diimplementasikan (defense in depth, beberapa lapis):**

1. **Proses terpisah total.** Bot ini adalah proses Node.js mandiri
   (`src/bot.js`), dijalankan lewat unit systemd-nya sendiri
   (`berseka-collector-bot.service`), **bukan** bagian dari
   `hermes-gateway.service` atau `9router.service` yang sudah berjalan.
2. **Kemampuan dibatasi ketat secara desain kode.** Bot ini hanya bisa:
   menerima command Telegram (`/mulai`, tombol inline), menerima foto,
   upload ke storage, dan tulis metadata. Tidak ada `child_process`,
   `exec`/`spawn`, tidak ada import/require modul Hermes/MCP apa pun di
   seluruh source tree `collector-bot/`. Tidak ada jalur kode yang mem-forward
   pesan user Telegram ke Claude Code atau sistem AI lain.
3. **User Linux terpisah & privilege terbatas.** Bot berjalan sebagai user
   sistem baru `berseka-bot` (bukan `maker`, user yang menjalankan
   hermes-gateway/9router). User ini `nologin` (tidak bisa login interaktif)
   dan hanya diberi akses baca ke folder `collector-bot/` (via POSIX ACL) plus
   akses baca-tulis ke `collector-bot/uploads/` dan `collector-bot/data/`.
4. **systemd sandboxing** di `berseka-collector-bot.service`:
   `ProtectSystem=strict`, `ProtectHome=true` + `ReadWritePaths` dibatasi ke
   folder proyek bot ini saja, `PrivateTmp=true`, `NoNewPrivileges=true`,
   `CapabilityBoundingSet=` kosong, `MemoryDenyWriteExecute=true`,
   `RestrictNamespaces=true`, dan beberapa proteksi kernel/IPC lain. Lihat
   file `.service` untuk daftar lengkap.
5. **Network minimal.** Bot pakai **long polling** Telegram (bukan webhook),
   jadi tidak perlu port inbound apa pun — tidak ada perubahan UFW/firewall.
   Outbound yang dibutuhkan hanya ke Telegram Bot API dan Cloudflare R2 API.
6. **Tidak ada shared state/IPC** dengan proses Hermes/gateway — tidak ada
   socket, pipe, shared file yang dibaca proses lain, atau shared database.

Jika ada rencana menambah fitur ke bot ini di masa depan, developer **wajib**
mempertahankan batasan-batasan di atas kecuali ada keputusan eksplisit &
terdokumentasi dari pemilik proyek untuk mengubah model keamanan ini.

---

## Arsitektur singkat

```
Mahasiswa (Telegram) --long polling--> bot.js --> storage.js --> R2 / uploads/ lokal
                                          |
                                          +--> manifest.js --> data/manifest.jsonl
```

Wizard flow: `/mulai` → pilih kelompok (1-32, dari `config/groups.json`) →
pilih jenis tong (Organik/Anorganik, inline keyboard) → kirim foto →
bot balas konfirmasi ✅.

Metadata yang disimpan per foto (di `data/manifest.jsonl`, satu baris JSON
per foto):

```json
{
  "kelompok_id": 7,
  "kelompok_label": "Kelompok 7",
  "jenis_tong": "organik",
  "timestamp_iso": "2026-08-28T02:00:38.907Z",
  "telegram_user_id": 123456789,
  "file_id": "AgAC...",
  "storage_mode": "local",
  "storage_key": "kelompok-7/organik/2026-08-28T02-00-38-907Z.jpg",
  "storage_location": "/path/atau/s3-uri"
}
```

Catatan: `telegram_user_id` disimpan **hanya untuk audit teknis internal**
(mis. debugging duplikasi/spam), **bukan** untuk identifikasi pribadi ke
publik atau dipublikasikan bersama dataset foto.

---

## Setup

### 1. Buat bot baru via @BotFather

1. Buka Telegram, chat ke `@BotFather`.
2. Kirim `/newbot`, ikuti instruksi (nama tampilan bebas, username harus
   unik & berakhiran `bot`, misal `makerindobot` jika masih tersedia — kalau
   sudah dipakai, pakai variasi seperti `berseka_collector_bot`).
3. BotFather akan memberi **token** (format `123456789:ABC-...`). Simpan
   token ini — **jangan** dibagikan/commit ke git.

### 2. Konfigurasi environment

```bash
cd collector-bot
cp .env.example .env
# edit .env, isi TELEGRAM_BOT_TOKEN dengan token dari langkah 1
```

Untuk mode storage, lihat bagian "Storage" di bawah.

### 3. Konfigurasi daftar kelompok

Edit `config/groups.json` — sudah berisi 32 kelompok default (`Kelompok 1`
s.d. `Kelompok 32`). Ganti `label` masing-masing dengan nama RT/RW/kelurahan
riil jika sudah tersedia dari koordinator (Pak Agus). **Jangan** ubah `id`
setelah data mulai masuk (dipakai di path storage & manifest).

### 4. Install dependencies

```bash
cd collector-bot
npm install
```

Project ini punya `package.json` sendiri, terpisah dari virtualenv Python
proyek ML (`berseka-ai/.venv`) — jangan dicampur.

### 5. Test lokal (opsional, sebelum deploy)

```bash
STORAGE_MODE=local node src/bot.js
```

Bot akan mulai long-polling. Chat ke bot dari Telegram, coba `/mulai`, pilih
kelompok & jenis tong, kirim foto. Cek `uploads/` dan `data/manifest.jsonl`.

### 6. Deploy sebagai systemd service

**Setup awal (sekali saja):**
```bash
sudo mkdir -p /opt/berseka-collector-bot
sudo bash collector-bot/deploy.sh   # sync kode + install deps + set ownership
sudo cp berseka-collector-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable berseka-collector-bot
sudo systemctl start berseka-collector-bot
sudo systemctl status berseka-collector-bot
journalctl -u berseka-collector-bot -f
```

**Setiap ada perubahan kode setelahnya** (JANGAN edit `/opt/berseka-collector-bot` langsung):
```bash
sudo bash collector-bot/deploy.sh
```
Skrip ini otomatis: sync file (rsync, exclude `node_modules`/`.env`/`uploads`/`data`),
`npm install --production` di lokasi deploy, perbaiki ownership ke user
`berseka-bot`, lalu restart service & verifikasi `active (running)`.

> **Catatan:** service ini dibuat untuk berjalan sebagai user Linux terpisah
> `berseka-bot` (dibuat via `sudo useradd --system --create-home --shell
> /usr/sbin/nologin berseka-bot`, sudah dilakukan). User ini diberi akses
> baca ke folder `collector-bot/` via POSIX ACL
> (`setfacl -R -m u:berseka-bot:rx collector-bot/`) dan akses baca-tulis ke
> `uploads/` & `data/`. Pastikan permission ini masih benar sebelum start.
>
> **Catatan jaringan (WAJIB untuk VPS dengan IPv6 bermasalah):** jika muncul
> `Polling error: EFATAL: AggregateError` berulang, kemungkinan besar VPS
> punya AAAA record IPv6 yang tidak reachable — lihat catatan di bagian
> "Status Deployment" di atas. Fix-nya ada di `Environment=NODE_OPTIONS=...`
> pada `.service` file, bukan di kode bot.

---

## Storage

Dua mode, diatur lewat `STORAGE_MODE` di `.env`:

- **`r2` (rekomendasi untuk go-live)** — upload ke Cloudflare R2
  (S3-compatible) via `@aws-sdk/client-s3`. Isi `R2_ACCOUNT_ID`,
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`,
  `R2_ENDPOINT` di `.env`. Path objek: `kelompok-{id}/{organik|anorganik}/{timestamp}.jpg`.
- **`local` (fallback sementara / dev)** — simpan ke folder lokal
  `collector-bot/uploads/` dengan struktur path yang sama.
  ⚠️ **PENTING:** ini hanya untuk testing/dev. Disk VPS gateway hanya
  ~19GB total, dipakai bareng banyak layanan lain. **Jangan** dipakai untuk
  menampung foto sungguhan dari 32 kelompok dalam skala nyata — pindahkan ke
  `r2` sebelum bot ini dipakai mahasiswa beneran.

### TODO sebelum go-live

- [ ] Provision bucket Cloudflare R2 (`berseka-collector-photos` atau nama
      lain) + buat API token/access key khusus.
- [ ] Isi kredensial R2 di `.env` produksi, set `STORAGE_MODE=r2`.
- [ ] Test upload end-to-end ke R2 (bukan hanya smoke test lokal).
- [ ] Setup sinkronisasi berkala manifest/foto ke Kaggle Dataset untuk tim ML
      (disebut di rencana awal, belum diimplementasi di bot ini).
- [ ] Isi label riil di `config/groups.json` setelah data RT/RW dari
      koordinator tersedia.

---

## Langkah selanjutnya untuk Daffa

1. Buat bot Telegram baru via @BotFather (lihat bagian Setup #1), dapatkan
   token.
2. Kasih token ke tim (Bayu) untuk diisi ke `.env` produksi di VPS — **jangan
   kirim token lewat channel yang tidak aman**.
3. Putuskan: pakai R2 dari awal, atau mulai dengan `STORAGE_MODE=local` untuk
   testing terbatas dulu sambil provisioning R2 berjalan paralel.
4. Setelah token & (idealnya) kredensial R2 siap, PM/Bayu akan
   `systemctl start berseka-collector-bot` dan melakukan test end-to-end.
5. Review `config/groups.json` — isi label kelompok riil jika sudah ada dari
   Pak Agus/koordinator KKN.
