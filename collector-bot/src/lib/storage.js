'use strict';
/**
 * storage.js
 *
 * =============================================================================
 * ISOLASI KEAMANAN
 * =============================================================================
 * Modul ini hanya melakukan DUA hal: (a) menulis buffer foto ke Cloudflare R2
 * via AWS S3-compatible SDK, atau (b) menulis ke disk lokal folder
 * collector-bot/uploads/ sebagai fallback sementara. TIDAK ADA eksekusi
 * command shell, TIDAK ADA panggilan ke API Hermes/MCP/gateway apa pun.
 * =============================================================================
 *
 * STORAGE_MODE=local adalah FALLBACK SEMENTARA saja. Disk VPS gateway hanya
 * ~19GB total, dipakai bareng banyak layanan lain. JANGAN biarkan mode local
 * dipakai untuk menampung foto sungguhan dari 32 kelompok dalam skala besar -
 * pindahkan ke R2 sebelum go-live (lihat README.md bagian "Storage" & TODO
 * di bawah).
 */

const fs = require('fs');
const path = require('path');

// TODO(go-live): pastikan STORAGE_MODE=r2 dan kredensial R2 sudah terisi di
// .env sebelum bot ini dipakai menerima foto sungguhan dari mahasiswa.
// Mode "local" hanya untuk development/testing menu bot tanpa R2.

function buildObjectKey({ groupId, jenisTong, timestampIso }) {
  // Path terorganisir: kelompok-{id}/{organik|anorganik}/{timestamp}.jpg
  const safeTimestamp = timestampIso.replace(/[:.]/g, '-');
  return `kelompok-${groupId}/${jenisTong}/${safeTimestamp}.jpg`;
}

class LocalStorage {
  constructor({ baseDir }) {
    this.baseDir = baseDir;
    fs.mkdirSync(this.baseDir, { recursive: true });
  }

  async putPhoto({ buffer, groupId, jenisTong, timestampIso }) {
    const key = buildObjectKey({ groupId, jenisTong, timestampIso });
    const fullPath = path.join(this.baseDir, key);
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });
    fs.writeFileSync(fullPath, buffer);
    return {
      storageMode: 'local',
      key,
      location: fullPath,
    };
  }
}

class R2Storage {
  constructor({ accountId, accessKeyId, secretAccessKey, bucketName, endpoint }) {
    // Lazy-require agar dependency @aws-sdk/client-s3 tidak wajib ada kalau
    // hanya dipakai mode local (mis. saat setup awal sebelum `npm install`
    // lengkap dijalankan di semua environment).
    const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
    this.PutObjectCommand = PutObjectCommand;
    this.bucketName = bucketName;
    this.client = new S3Client({
      region: 'auto',
      endpoint,
      credentials: { accessKeyId, secretAccessKey },
    });
  }

  async putPhoto({ buffer, groupId, jenisTong, timestampIso }) {
    const key = buildObjectKey({ groupId, jenisTong, timestampIso });
    await this.client.send(
      new this.PutObjectCommand({
        Bucket: this.bucketName,
        Key: key,
        Body: buffer,
        ContentType: 'image/jpeg',
      })
    );
    return {
      storageMode: 'r2',
      key,
      location: `s3://${this.bucketName}/${key}`,
    };
  }
}

function createStorage(config) {
  if (config.storageMode === 'r2') {
    return new R2Storage(config.r2);
  }
  return new LocalStorage({ baseDir: config.localUploadDir });
}

module.exports = { createStorage, buildObjectKey };
