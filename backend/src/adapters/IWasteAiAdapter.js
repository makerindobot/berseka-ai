'use strict';
/**
 * IWasteAiAdapter — Kontrak Adapter Pattern untuk integrasi Backend Node.js
 * dengan model AI BERSEKA (Backlog 7).
 *
 * TUJUAN: Backend (routes, scheduler, business logic scan) tidak boleh
 * bergantung langsung pada detail implementasi model serving (FastAPI HTTP,
 * gRPC, atau bahkan model lokal di masa depan). Semua akses ke kapabilitas
 * AI HARUS lewat interface ini, supaya:
 *   1. Mudah di-mock untuk testing (lihat adapters/mockWasteAiAdapter.js)
 *   2. Mudah diganti implementasinya (mis. dari HTTP ke gRPC, atau model
 *      di-load in-process) tanpa mengubah kode business logic manapun
 *   3. Kontrak jelas & terdokumentasi satu tempat — bukan tersebar
 *
 * // TODO: definisi ini disusun oleh Dimas (Backend/ML Engineer) berdasarkan
 * // skema kontrak /predict & /ws/predict yang SUDAH diimplementasikan di
 * // Backlog 6 (lihat api/schemas/predict_schema.py di root repo Python).
 * // Belum ada dokumen interface asli terpisah dari Daffa yang ditemukan di
 * // repo saat Backlog 7 dimulai — PM WAJIB minta review & sign-off Daffa
 * // atas kontrak ini sebelum dianggap final, terutama penamaan method &
 * // bentuk parameter/return value.
 *
 * Semua implementasi WAJIB extends class ini dan override setiap method.
 * Base class melempar error eksplisit kalau method belum di-override,
 * supaya kesalahan implementasi ketahuan cepat (fail-fast), bukan diam-diam
 * mengembalikan undefined.
 */

class IWasteAiAdapter {
  /**
   * Analisis 1 foto tong sampah secara sinkron (request-response biasa).
   * Dipetakan ke endpoint HTTP POST /predict di sisi model serving Python
   * (Backlog 6) pada implementasi FastApiWasteAiAdapter.
   *
   * @param {Buffer} imageBuffer - Isi file gambar (JPEG/PNG/WebP), sudah
   *   dibaca penuh ke memori (ukuran wajar untuk foto kamera HP, bukan
   *   video/stream — untuk itu pakai analyzeStream()).
   * @param {object} [options]
   * @param {string} [options.vendorId] - ID tong sampah/vendor pemindai,
   *   diteruskan apa adanya ke model serving untuk lookup vendorName.
   * @param {string} [options.mimeType] - Content-Type file (default
   *   "image/jpeg" jika tidak diisi).
   * @returns {Promise<WasteAiPredictionResult>}
   * @throws {WasteAiAdapterError} jika model serving tidak bisa dihubungi,
   *   timeout, atau mengembalikan response tidak valid. TIDAK melempar
   *   error untuk kasus bisnis "tidak ada sampah terdeteksi" — itu
   *   direpresentasikan sebagai field `noWasteDetected: true` pada hasil,
   *   supaya caller bisa membedakan "gagal teknis" vs "gagal deteksi".
   */
  async analyzeImage(imageBuffer, options = {}) {
    throw new Error(
      `${this.constructor.name} belum meng-override analyzeImage() — implementasi tidak lengkap.`
    );
  }

  /**
   * Cek ketersediaan/kesehatan model serving di balik adapter ini.
   * Dipetakan ke GET /healthz di sisi FastAPI (Backlog 6).
   *
   * @returns {Promise<{ ok: boolean, detail?: object, error?: string }>}
   */
  async healthCheck() {
    throw new Error(
      `${this.constructor.name} belum meng-override healthCheck() — implementasi tidak lengkap.`
    );
  }

  /**
   * Nama/identitas implementasi adapter, untuk logging & audit trail
   * (mis. "fastapi-mock-v0" saat masih pakai mock classifier Backlog 6,
   * "fastapi-yolov8-v1" setelah model asli Backlog 5 di-deploy).
   *
   * @returns {string}
   */
  get adapterName() {
    throw new Error(
      `${this.constructor.name} belum meng-override getter adapterName — implementasi tidak lengkap.`
    );
  }
}

/**
 * @typedef {object} WasteAiBoundingBox
 * @property {number} x_center
 * @property {number} y_center
 * @property {number} width
 * @property {number} height
 */

/**
 * @typedef {object} WasteAiDetection
 * @property {"ORGANIC"|"NON_ORGANIC"|"MIXED"} label
 * @property {number} confidence
 * @property {WasteAiBoundingBox} bbox
 */

/**
 * @typedef {object} WasteAiPredictionResult
 * Bentuk hasil NORMALIZED yang dikembalikan SEMUA implementasi adapter,
 * TIDAK peduli bentuk asli response dari model serving (field ini sengaja
 * dibuat camelCase konsisten gaya JS, BEDA dari snake_case sebagian field
 * asli Python contract seperti `organik_percent` -- adapter yang
 * bertanggung jawab menerjemahkan/mapping, bukan business logic backend).
 *
 * @property {string} requestId
 * @property {boolean} noWasteDetected - true jika model tidak yakin ada
 *   sampah terdeteksi (confidence < ambang, kode asli NO_WASTE_DETECTED).
 *   Jika true, field lain selain requestId/errorMessage bernilai null.
 * @property {string|null} errorMessage - pesan error manusiawi jika
 *   noWasteDetected true, null jika sukses.
 * @property {"ORGANIC"|"NON_ORGANIC"|"MIXED"|null} detectedType
 * @property {number|null} confidenceScore
 * @property {number|null} estimatedVolumeLiter
 * @property {number|null} organikPercent
 * @property {number|null} nonOrganikPercent
 * @property {WasteAiDetection[]} detections
 * @property {string|null} vendorName
 * @property {string|null} annotatedImageBase64
 * @property {number|null} serverLatencyMs - null untuk analyzeImage()
 *   HTTP biasa kecuali diukur eksplisit oleh adapter.
 */

/**
 * Error khusus adapter — dilempar untuk kegagalan TEKNIS (network, timeout,
 * response tidak valid), BUKAN untuk kasus bisnis NO_WASTE_DETECTED (lihat
 * WasteAiPredictionResult.noWasteDetected).
 */
class WasteAiAdapterError extends Error {
  constructor(message, { cause, code } = {}) {
    super(message, { cause });
    this.name = 'WasteAiAdapterError';
    this.code = code || 'WASTE_AI_ADAPTER_ERROR';
  }
}

module.exports = { IWasteAiAdapter, WasteAiAdapterError };
