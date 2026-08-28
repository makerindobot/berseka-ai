'use strict';
/**
 * Skema database SQLite untuk histori scan tong sampah (Backlog 7).
 *
 * Pakai `node:sqlite` bawaan Node.js (stabil sejak Node 22.5, tersedia di
 * Node 26 yang terpasang di gateway) — SENGAJA tidak pakai better-sqlite3
 * (native addon, butuh compile toolchain) atau Postgres/MySQL terpisah
 * (overkill untuk skala proyek KKN 32 kelompok + beban RAM gateway 1.9GB
 * sudah dipakai monitoring Netdata, lihat catatan VPS di memori PM).
 *
 * Tabel:
 *   scans        - 1 baris per hasil scan foto tong sampah
 *   scan_windows - jadwal scan pagi/sore per hari (dipakai validasi Backlog 7 poin 4)
 */

const { DatabaseSync } = require('node:sqlite');
const path = require('node:path');
const fs = require('node:fs');

function openDatabase(dbPath) {
  const dir = path.dirname(dbPath);
  if (dir && dir !== ':memory:') {
    fs.mkdirSync(dir, { recursive: true });
  }
  const db = new DatabaseSync(dbPath);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA foreign_keys = ON;');
  migrate(db);
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS scans (
      id                    INTEGER PRIMARY KEY AUTOINCREMENT,
      request_id            TEXT NOT NULL,
      vendor_id             TEXT,
      vendor_name           TEXT,
      warga_id              TEXT,
      kelompok_kkn_id       TEXT,
      scan_window           TEXT CHECK (scan_window IN ('pagi', 'sore', 'manual')) NOT NULL DEFAULT 'manual',
      no_waste_detected     INTEGER NOT NULL DEFAULT 0,
      error_message         TEXT,
      detected_type         TEXT CHECK (detected_type IN ('ORGANIC', 'NON_ORGANIC', 'MIXED') OR detected_type IS NULL),
      confidence_score      REAL,
      estimated_volume_liter REAL,
      organik_percent       REAL,
      non_organik_percent   REAL,
      detections_json       TEXT,
      annotated_image_ref   TEXT,
      server_latency_ms     REAL,
      adapter_name          TEXT NOT NULL,
      created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
  `);

  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_scans_vendor_id ON scans (vendor_id);
  `);
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_scans_kelompok_kkn_id ON scans (kelompok_kkn_id);
  `);
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at);
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS scan_windows (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      window_name TEXT CHECK (window_name IN ('pagi', 'sore')) NOT NULL UNIQUE,
      start_time  TEXT NOT NULL,
      end_time    TEXT NOT NULL
    );
  `);

  const existing = db.prepare('SELECT COUNT(*) as c FROM scan_windows').get();
  if (existing.c === 0) {
    const insert = db.prepare(
      'INSERT INTO scan_windows (window_name, start_time, end_time) VALUES (?, ?, ?)'
    );
    // Rentang default indikatif — PM/Daffa perlu konfirmasi jam pasti
    // program Coblong (belum ada di dokumen sumber yang tersedia).
    insert.run('pagi', '05:00', '09:00');
    insert.run('sore', '15:00', '18:00');
  }
}

module.exports = { openDatabase };
