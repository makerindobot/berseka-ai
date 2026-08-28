'use strict';
/**
 * config.js
 *
 * =============================================================================
 * ISOLASI KEAMANAN (baca sebelum ubah apa pun)
 * =============================================================================
 * File ini HANYA membaca environment variables & file JSON konfigurasi lokal
 * proyek ini. Tidak ada koneksi ke Hermes API, MCP tools, atau gateway
 * control plane VPS dalam bentuk apa pun. Bot ini didesain SENGAJA untuk
 * berjalan sebagai proses Node.js yang berdiri sendiri, terpisah total dari
 * hermes-gateway.service / 9router.service.
 * =============================================================================
 */

require('dotenv').config();
const fs = require('fs');
const path = require('path');

function loadGroups(groupsConfigPath) {
  const resolved = path.resolve(groupsConfigPath);
  const raw = fs.readFileSync(resolved, 'utf8');
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed.groups) || parsed.groups.length === 0) {
    throw new Error(`groups.json tidak valid atau kosong: ${resolved}`);
  }
  return parsed.groups;
}

function loadConfig() {
  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  if (!botToken) {
    throw new Error(
      'TELEGRAM_BOT_TOKEN belum diset. Salin .env.example ke .env dan isi token ' +
        'dari @BotFather (lihat README.md).'
    );
  }

  const storageMode = (process.env.STORAGE_MODE || 'local').toLowerCase();
  if (!['r2', 'local'].includes(storageMode)) {
    throw new Error(`STORAGE_MODE tidak valid: "${storageMode}". Gunakan "r2" atau "local".`);
  }

  const groupsConfigPath = process.env.GROUPS_CONFIG_PATH || './config/groups.json';
  const manifestPath = process.env.MANIFEST_PATH || './data/manifest.jsonl';
  const localUploadDir = process.env.LOCAL_UPLOAD_DIR || './uploads';

  const r2 = {
    accountId: process.env.R2_ACCOUNT_ID || '',
    accessKeyId: process.env.R2_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY || '',
    bucketName: process.env.R2_BUCKET_NAME || 'berseka-collector-photos',
    endpoint: process.env.R2_ENDPOINT || '',
  };

  if (storageMode === 'r2') {
    const missing = ['accountId', 'accessKeyId', 'secretAccessKey', 'endpoint'].filter(
      (k) => !r2[k]
    );
    if (missing.length > 0) {
      throw new Error(
        `STORAGE_MODE=r2 tapi kredensial R2 belum lengkap (kurang: ${missing.join(
          ', '
        )}). Isi .env atau set STORAGE_MODE=local untuk fallback sementara.`
      );
    }
  }

  return {
    botToken,
    storageMode,
    groups: loadGroups(groupsConfigPath),
    manifestPath: path.resolve(manifestPath),
    localUploadDir: path.resolve(localUploadDir),
    r2,
  };
}

module.exports = { loadConfig };
