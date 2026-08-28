#!/usr/bin/env bash
# deploy.sh — Sync collector-bot/ (source Git) ke /opt/berseka-collector-bot
# (deployment runtime, di luar /home karena systemd ProtectHome=true).
#
# KENAPA ADA 2 LOKASI: lihat README.md bagian "Status Deployment (Live)".
# Singkatnya: proses systemd sandboxed (berseka-bot user) tidak bisa akses
# apa pun di bawah /home meski ProtectHome punya exception, jadi runtime
# HARUS di /opt/. Source code kanonis TETAP di repo Git ini.
#
# Skrip ini menggantikan `sudo cp -r` manual yang disebutkan di README
# sebagai gap sementara — dibuat untuk mencegah drift diam-diam antara
# source repo & kode yang benar-benar jalan di systemd service.
#
# Pemakaian:
#   sudo bash collector-bot/deploy.sh
#
# Yang dilakukan:
#   1. rsync isi collector-bot/ (kecuali node_modules, .env, .git) ke /opt/
#   2. npm install --production di /opt/ (dependencies bisa beda dari lokal)
#   3. Perbaiki ownership ke user berseka-bot:berseka-bot
#   4. Restart service & tunggu konfirmasi "active (running)"
#   5. Tampilkan ringkasan diff terakhir (apa yang berubah) untuk audit

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="/opt/berseka-collector-bot"
SERVICE_NAME="berseka-collector-bot.service"
SERVICE_USER="berseka-bot"

if [[ $EUID -ne 0 ]]; then
  echo "[deploy] Skrip ini butuh sudo (perlu tulis ke $DEPLOY_DIR & restart systemd service)." >&2
  echo "[deploy] Jalankan: sudo bash $0" >&2
  exit 1
fi

if [[ ! -d "$DEPLOY_DIR" ]]; then
  echo "[deploy] ERROR: $DEPLOY_DIR belum ada. Setup awal (bukan skrip ini) diperlukan dulu." >&2
  echo "[deploy] Lihat README.md bagian 'Deploy sebagai systemd service'." >&2
  exit 1
fi

echo "[deploy] Sinkronisasi source code: $SOURCE_DIR -> $DEPLOY_DIR"
rsync -a --delete \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '.git' \
  --exclude 'uploads' \
  --exclude 'data' \
  "$SOURCE_DIR"/ "$DEPLOY_DIR"/

echo "[deploy] Memperbaiki ownership ke $SERVICE_USER:$SERVICE_USER"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEPLOY_DIR"

echo "[deploy] Install dependencies produksi di $DEPLOY_DIR"
sudo -u "$SERVICE_USER" bash -c "cd '$DEPLOY_DIR' && npm install --omit=dev --no-audit --no-fund"

echo "[deploy] Restart $SERVICE_NAME"
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[deploy] OK — $SERVICE_NAME active (running)."
else
  echo "[deploy] GAGAL — $SERVICE_NAME tidak aktif setelah restart! Cek log:" >&2
  echo "         sudo journalctl -u $SERVICE_NAME -n 50 --no-pager" >&2
  exit 1
fi

echo "[deploy] Selesai. Pantau log 30 detik untuk pastikan tidak ada error langsung setelah deploy:"
echo "         sudo journalctl -u $SERVICE_NAME -f"
