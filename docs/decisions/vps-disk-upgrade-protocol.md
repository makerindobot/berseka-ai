# Protokol Upgrade Disk VPS mps-gateway (19GB → 40GB)

**Tanggal:** 28 Agustus 2026
**Alasan:** Disk gateway mepet (sisa 5GB dari 19GB, 73% terpakai) — tidak
cukup untuk akuisisi dataset BERSEKA AI (6 dataset Kaggle, total 6.79GB)
+ ruang training pipeline (checkpoint model, dll) ke depan.

---

## SEBELUM shutdown (sudah dicek Dimas/PM — status: AMAN)

- [x] Tidak ada proses berat/background job milik sesi ini yang masih jalan
      (server FastAPI test port 8500/8811/8123, backend Node.js test port
      4500 — semua sudah dimatikan bersih sebelum permintaan upgrade ini)
- [x] Semua kerjaan sampai saat ini SUDAH ter-commit & ter-push ke git
      (`makerindobot/berseka-ai`, commit terakhir: modul quality-gate +
      kalibrasi kamera, Backlog 3 & 4)
- [x] Tidak ada proses download dataset yang sedang berjalan (baru tahap
      cek ukuran/ketersediaan via `kaggle datasets list`, belum mulai
      `download_all()`)
- [ ] **Layanan yang TERDAMPAK reboot** (auto-restart via systemd, tapi
      perlu diverifikasi manual setelah upgrade — lihat checklist bawah):
  - `9router.service` (Hermes AI Gateway — termasuk sesi chat ini sendiri)
  - `berseka-collector-bot.service` (bot Telegram pengumpul foto KKN)
  - `netdata.service` (monitoring parent — child node lain streaming ke sini)

---

## Proses Upgrade (dilakukan Daffa via panel IDCloudHost)

1. Matikan VPS dari panel IDCloudHost (`my.idcloudhost.com`)
2. Resize/upgrade disk ke 40GB melalui panel
3. Nyalakan kembali VPS
4. **Kabari Hermes** begitu VPS hidup lagi (chat ini akan terputus saat VPS
   mati — sesi baru akan otomatis reconnect begitu gateway hidup lagi;
   kalau tidak otomatis reconnect dalam beberapa menit, restart manual
   percakapan)

**Catatan teknis untuk Daffa:** disk `/dev/vda1` di VPS ini adalah partisi
tunggal (`lsblk` menunjukkan `vda1` 19GB dari total block device `vda`
20GB — ada sedikit ruang tak terpakai di block device fisik selain
partisi boot/efi). Provider cloud (IDCloudHost) biasanya cuma perlu
resize block device via panel; partisi & filesystem root **mungkin perlu
di-resize manual** dari dalam VPS setelah disk fisik bertambah (`growpart`
+ `resize2fs`/`xfs_growfs` tergantung filesystem) — **ini bagian yang akan
Hermes verifikasi & eksekusi di langkah "Setelah VPS Menyala" di bawah**,
jangan asumsikan otomatis membesar sendiri.

---

## SETELAH VPS Menyala Kembali — Checklist Verifikasi (dieksekusi Hermes)

### 1. Verifikasi disk benar-benar bertambah
```bash
lsblk                  # cek block device vda sekarang 40GB?
df -h /                # cek filesystem root SUDAH ikut membesar?
```
Jika filesystem belum ikut membesar meski block device sudah 40GB:
```bash
sudo growpart /dev/vda 1      # resize partisi vda1
sudo resize2fs /dev/vda1       # (jika ext4) resize filesystem
# atau: sudo xfs_growfs /       # jika filesystem XFS
df -h /                        # verifikasi ulang, harus ~40GB sekarang
```

### 2. Verifikasi layanan kritis hidup normal
```bash
systemctl status 9router.service --no-pager
systemctl status berseka-collector-bot.service --no-pager
systemctl status netdata.service --no-pager
```
Semua harus `active (running)`. Kalau ada yang gagal start otomatis,
`systemctl restart <nama-service>` lalu cek log (`journalctl -u <nama> -n 50`).

### 3. Verifikasi monitoring child node masih streaming
Cek dashboard Netdata (via tunnel SSH seperti biasa) — pastikan child
node (Sespima2026 & lainnya) masih terhubung setelah parent restart.

### 4. Verifikasi cron job alert masih aktif
```bash
# dari sesi Hermes: cronjob action=list, cari "netdata-gateway-alerts"
```
Pastikan job tidak ter-pause/hilang akibat restart.

### 5. Verifikasi bot collector-bot: masalah polling error SEBELUM upgrade
**PENTING — bug yang belum diperbaiki**: sebelum upgrade ini, bot
`@bersekabot` mengalami `Polling error: EFATAL: AggregateError` berulang
sejak 28 Agustus ~11:28 WIB (root cause belum didiagnosis — kemungkinan
masalah koneksi long-polling ke Telegram API, BUKAN masalah disk).
**Folder `data/raw/field-capture/` masih 0 foto** — belum ada satu pun
data lapangan masuk dari 32 kelompok KKN.
Setelah VPS hidup kembali:
```bash
sudo systemctl restart berseka-collector-bot.service
sudo journalctl -u berseka-collector-bot.service -f   # pantau live, kirim 1 foto test dari Telegram
```
Jika error masih muncul setelah restart, perlu investigasi lebih lanjut
(kemungkinan token/network/library `node-telegram-bot-api` versi bug) —
**ini prioritas tinggi**, karena tanpa bot jalan, tidak ada data lapangan
yang bisa dikumpulkan sama sekali walau mahasiswa sudah diberi instruksi.

### 6. Lanjutkan Backlog 1 — Download Dataset (baru bisa jalan setelah disk cukup)
```bash
cd /home/maker/damaker-studio-projects/berseka-ai
.venv/bin/python -m src.preprocessing.dataset_acquisition --data-root data
```
Ukuran total 6 dataset: **6.79 GB** (taco_yolo 0.23GB, taco_coco 2.79GB,
garbage_classification_v2 1.07GB, alistairking 0.90GB, waste_segregation
1.17GB, realwaste 0.64GB). Dengan disk 40GB (dan sisa lama ~5GB + 20GB
baru = idealnya ~25GB free setelah resize), aman untuk download SEMUA 6
dataset sekaligus tanpa perlu skip `taco_coco` lagi.

Verifikasi pasca-download:
- Cek `data/raw/<key>/` masing-masing berisi file (bukan kosong)
- Jalankan ulang `df -h /` — pastikan masih ada buffer aman (jangan sampai
  >85% terpakai) sebelum lanjut preprocessing/training

---

## Ringkasan Status Sebelum Jeda

- **Backlog 1 (Dataset)**: dokumen keputusan `dataset-decision.md` sudah
  final, TAPI **belum ada 1 byte dataset yang benar-benar terunduh** ke
  disk — baru diverifikasi ketersediaan via Kaggle API. Ini yang akan
  dieksekusi begitu disk siap.
- **Data lapangan (collector-bot)**: 0 foto masuk, bot sedang error
  polling — perlu diagnosis terpisah dari isu disk.
- Semua progres kode (Backlog 2, 3, 4, 6, 7) aman, sudah commit & push ke
  git — tidak ada risiko kehilangan data akibat restart VPS.
