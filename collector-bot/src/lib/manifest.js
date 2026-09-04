'use strict';
/**
 * manifest.js
 *
 * Menyimpan metadata setiap foto sebagai satu baris JSON (JSONL) di
 * collector-bot/data/manifest.jsonl. Hanya file I/O lokal - tidak ada
 * database eksternal, tidak ada panggilan API di luar yang eksplisit
 * didokumentasikan di README.md.
 */

const fs = require('fs');
const path = require('path');

const TARGET_PER_GROUP_PER_TYPE = 100; // 100 organik + 100 anorganik = 200 total

class ManifestWriter {
  constructor({ manifestPath }) {
    this.manifestPath = manifestPath;
    fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  }

  append(entry) {
    const line = JSON.stringify(entry) + '\n';
    fs.appendFileSync(this.manifestPath, line, 'utf8');
  }

  /** Baca semua entri manifest (return array of objects) */
  readAll() {
    if (!fs.existsSync(this.manifestPath)) return [];
    const content = fs.readFileSync(this.manifestPath, 'utf8').trim();
    if (!content) return [];
    return content.split('\n').map(line => JSON.parse(line));
  }

  /** Hitung progress per kelompok per jenis tong */
  getProgress() {
    const entries = this.readAll();
    const stats = {};
    for (const entry of entries) {
      const groupId = entry.kelompok_id;
      const groupLabel = entry.kelompok_label;
      const jenis = entry.jenis_tong;
      if (!stats[groupId]) {
        stats[groupId] = {
          groupId,
          groupLabel,
          organik: 0,
          anorganik: 0,
          total: 0,
        };
      }
      if (jenis === 'organik') stats[groupId].organik++;
      else if (jenis === 'anorganik') stats[groupId].anorganik++;
      stats[groupId].total++;
    }
    return stats;
  }

  /** Generate ringkasan progress untuk balasan otomatis */
  getProgressSummary(groupId) {
    const stats = this.getProgress();
    const group = stats[groupId];
    if (!group) return null;

    const orgPct = Math.round((group.organik / TARGET_PER_GROUP_PER_TYPE) * 100);
    const anorgPct = Math.round((group.anorganik / TARGET_PER_GROUP_PER_TYPE) * 100);
    const totalPct = Math.round((group.total / (TARGET_PER_GROUP_PER_TYPE * 2)) * 100);

    const progressBar = (pct) => {
      const filled = Math.min(Math.round(pct / 10), 10);
      return '█'.repeat(filled) + '░'.repeat(10 - filled) + ` ${pct}%`;
    };

    return {
      groupLabel: group.groupLabel,
      organik: { count: group.organik, target: TARGET_PER_GROUP_PER_TYPE, pct: orgPct, bar: progressBar(orgPct) },
      anorganik: { count: group.anorganik, target: TARGET_PER_GROUP_PER_TYPE, pct: anorgPct, bar: progressBar(anorgPct) },
      total: { count: group.total, target: TARGET_PER_GROUP_PER_TYPE * 2, pct: totalPct },
    };
  }

  /** Alias untuk kompatibilitas dengan command /progress */
  getProgressSummaryAll() {
    return this.getProgress();
  }
}

module.exports = { ManifestWriter, TARGET_PER_GROUP_PER_TYPE };
