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

class ManifestWriter {
  constructor({ manifestPath }) {
    this.manifestPath = manifestPath;
    fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  }

  append(entry) {
    const line = JSON.stringify(entry) + '\n';
    fs.appendFileSync(this.manifestPath, line, 'utf8');
  }
}

module.exports = { ManifestWriter };
