'use strict';
/**
 * ScanRepository — akses data histori scan (Backlog 7 poin 3: "Skema
 * database untuk histori scan per warga/tong sampah/waktu").
 *
 * Dipisahkan dari route handler supaya query SQL terpusat & mudah diuji
 * tanpa perlu spin up Express (lihat tests/scanRepository.test.js).
 */

class ScanRepository {
  /** @param {import('node:sqlite').DatabaseSync} db */
  constructor(db) {
    this.db = db;
  }

  /**
   * @param {object} params
   * @param {string} params.requestId
   * @param {string} [params.vendorId]
   * @param {string} [params.wargaId]
   * @param {string} [params.kelompokKknId]
   * @param {string} params.scanWindow - "pagi" | "sore" | "manual"
   * @param {import('../adapters/IWasteAiAdapter').WasteAiPredictionResult} params.result
   * @param {string} params.adapterName
   * @returns {number} id baris yang baru dibuat
   */
  insertScan({ requestId, vendorId, wargaId, kelompokKknId, scanWindow, result, adapterName }) {
    const stmt = this.db.prepare(`
      INSERT INTO scans (
        request_id, vendor_id, vendor_name, warga_id, kelompok_kkn_id, scan_window,
        no_waste_detected, error_message, detected_type, confidence_score,
        estimated_volume_liter, organik_percent, non_organik_percent,
        detections_json, annotated_image_ref, server_latency_ms, adapter_name
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const info = stmt.run(
      requestId,
      vendorId ?? null,
      result.vendorName ?? null,
      wargaId ?? null,
      kelompokKknId ?? null,
      scanWindow,
      result.noWasteDetected ? 1 : 0,
      result.errorMessage ?? null,
      result.detectedType ?? null,
      result.confidenceScore ?? null,
      result.estimatedVolumeLiter ?? null,
      result.organikPercent ?? null,
      result.nonOrganikPercent ?? null,
      result.detections ? JSON.stringify(result.detections) : null,
      // annotatedImageBase64 SENGAJA tidak disimpan penuh di DB (bisa besar,
      // membebani RAM/disk gateway 1.9GB) — hanya simpan referensi/flag.
      // TODO Backlog 7 lanjutan: upload ke object storage (pola sama dgn
      // collector-bot/src/lib/storage.js) dan simpan URL-nya di sini.
      result.annotatedImageBase64 ? 'stored_in_response_only' : null,
      result.serverLatencyMs ?? null,
      adapterName
    );
    return info.lastInsertRowid;
  }

  /** @param {number} id */
  getScanById(id) {
    const row = this.db.prepare('SELECT * FROM scans WHERE id = ?').get(id);
    if (!row) return null;
    return this._deserialize(row);
  }

  /**
   * @param {object} [filters]
   * @param {string} [filters.vendorId]
   * @param {string} [filters.kelompokKknId]
   * @param {number} [filters.limit]
   */
  listScans({ vendorId, kelompokKknId, limit = 50 } = {}) {
    const clauses = [];
    const args = [];
    if (vendorId) {
      clauses.push('vendor_id = ?');
      args.push(vendorId);
    }
    if (kelompokKknId) {
      clauses.push('kelompok_kkn_id = ?');
      args.push(kelompokKknId);
    }
    const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    const rows = this.db
      .prepare(`SELECT * FROM scans ${where} ORDER BY created_at DESC LIMIT ?`)
      .all(...args, limit);
    return rows.map((r) => this._deserialize(r));
  }

  /**
   * Statistik kepatuhan sederhana per kelompok KKN — dasar untuk laporan
   * Backlog 8 (dashboard). Menghitung rata-rata organik_percent dan jumlah
   * scan valid (bukan NO_WASTE_DETECTED).
   * @param {string} kelompokKknId
   */
  getComplianceSummary(kelompokKknId) {
    const row = this.db
      .prepare(
        `SELECT
           COUNT(*) as total_scans,
           SUM(CASE WHEN no_waste_detected = 0 THEN 1 ELSE 0 END) as valid_scans,
           AVG(CASE WHEN no_waste_detected = 0 THEN organik_percent END) as avg_organik_percent
         FROM scans WHERE kelompok_kkn_id = ?`
      )
      .get(kelompokKknId);
    return {
      kelompokKknId,
      totalScans: row.total_scans,
      validScans: row.valid_scans ?? 0,
      avgOrganikPercent: row.avg_organik_percent ?? null,
    };
  }

  getScanWindows() {
    return this.db.prepare('SELECT * FROM scan_windows').all();
  }

  /** @private */
  _deserialize(row) {
    return {
      ...row,
      no_waste_detected: Boolean(row.no_waste_detected),
      detections: row.detections_json ? JSON.parse(row.detections_json) : [],
    };
  }
}

module.exports = { ScanRepository };
