'use strict';
/**
 * FastApiWasteAiAdapter — implementasi IWasteAiAdapter yang memanggil
 * Model Serving API FastAPI (Backlog 6: POST /predict, GET /healthz).
 *
 * Pemetaan field (snake_case Python -> camelCase JS ternormalisasi, lihat
 * IWasteAiAdapter.js untuk penjelasan lengkap kenapa mapping ini perlu):
 *   detectedType          -> detectedType
 *   confidenceScore       -> confidenceScore
 *   estimatedVolumeLiter  -> estimatedVolumeLiter
 *   organik_percent       -> organikPercent
 *   non_organik_percent   -> nonOrganikPercent
 *   detections[]          -> detections[] (bentuk sama, sudah camelCase)
 *   vendorName            -> vendorName
 *   annotatedImageBase64  -> annotatedImageBase64
 *
 * Menggunakan `fetch` global bawaan Node.js (tersedia sejak Node 18+,
 * tidak butuh axios/node-fetch tambahan) dan `FormData`/`Blob` global
 * (Node 18+) untuk multipart upload — dependency minimal, konsisten
 * dengan prinsip least-dependency proyek ini.
 */

const { IWasteAiAdapter, WasteAiAdapterError } = require('./IWasteAiAdapter');

const DEFAULT_TIMEOUT_MS = 15_000;

class FastApiWasteAiAdapter extends IWasteAiAdapter {
  /**
   * @param {object} opts
   * @param {string} opts.baseUrl - mis. "http://127.0.0.1:8000" (tanpa
   *   trailing slash, tapi kalau ada trailing slash tetap dinormalisasi).
   * @param {number} [opts.timeoutMs] - timeout per request (default 15s;
   *   mock classifier saat ini biasanya <200ms, tapi model YOLOv8 asli
   *   nanti bisa lebih lama — beri buffer wajar, bukan sekadar copy angka
   *   mock).
   */
  constructor({ baseUrl, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
    super();
    if (!baseUrl) {
      throw new WasteAiAdapterError(
        'FastApiWasteAiAdapter butuh baseUrl (mis. process.env.WASTE_AI_API_BASE_URL) — tidak boleh kosong.'
      );
    }
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.timeoutMs = timeoutMs;
  }

  get adapterName() {
    return 'fastapi-http-adapter';
  }

  async healthCheck() {
    try {
      const resp = await this._fetchWithTimeout(`${this.baseUrl}/healthz`, { method: 'GET' });
      if (!resp.ok) {
        return { ok: false, error: `HTTP ${resp.status} dari ${this.baseUrl}/healthz` };
      }
      const body = await resp.json();
      return { ok: true, detail: body };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }

  async analyzeImage(imageBuffer, options = {}) {
    if (!Buffer.isBuffer(imageBuffer) || imageBuffer.length === 0) {
      throw new WasteAiAdapterError('analyzeImage() butuh imageBuffer non-kosong (Buffer).', {
        code: 'INVALID_IMAGE_BUFFER',
      });
    }

    const mimeType = options.mimeType || 'image/jpeg';
    const form = new FormData();
    const blob = new Blob([imageBuffer], { type: mimeType });
    form.append('image', blob, 'scan.jpg');
    if (options.vendorId) {
      form.append('vendorId', options.vendorId);
    }

    let resp;
    try {
      resp = await this._fetchWithTimeout(`${this.baseUrl}/predict`, {
        method: 'POST',
        body: form,
      });
    } catch (err) {
      throw new WasteAiAdapterError(
        `Gagal menghubungi model serving API di ${this.baseUrl}/predict: ${err.message}`,
        { cause: err, code: 'NETWORK_ERROR' }
      );
    }

    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new WasteAiAdapterError(
        `Model serving API mengembalikan HTTP ${resp.status}: ${text.slice(0, 500)}`,
        { code: 'UPSTREAM_HTTP_ERROR' }
      );
    }

    let body;
    try {
      body = await resp.json();
    } catch (err) {
      throw new WasteAiAdapterError('Response model serving API bukan JSON valid.', {
        cause: err,
        code: 'INVALID_RESPONSE_BODY',
      });
    }

    return this._normalizeResponse(body);
  }

  /**
   * @private
   * Terjemahkan body JSON mentah dari FastAPI (bisa berupa PredictResponse
   * sukses ATAU ErrorResponse dgn code NO_WASTE_DETECTED) menjadi
   * WasteAiPredictionResult ternormalisasi.
   */
  _normalizeResponse(body) {
    if (body && body.error) {
      return {
        requestId: body.requestId || null,
        noWasteDetected: body.error.code === 'NO_WASTE_DETECTED',
        errorMessage: body.error.message || 'Error tidak diketahui dari model serving API.',
        detectedType: null,
        confidenceScore: null,
        estimatedVolumeLiter: null,
        organikPercent: null,
        nonOrganikPercent: null,
        detections: [],
        vendorName: null,
        annotatedImageBase64: null,
        serverLatencyMs: body.serverLatencyMs ?? null,
      };
    }

    const requiredFields = [
      'requestId',
      'detectedType',
      'confidenceScore',
      'estimatedVolumeLiter',
      'organik_percent',
      'non_organik_percent',
      'detections',
      'annotatedImageBase64',
    ];
    const missing = requiredFields.filter((f) => !(f in (body || {})));
    if (missing.length > 0) {
      throw new WasteAiAdapterError(
        `Response model serving API kehilangan field wajib: ${missing.join(', ')}`,
        { code: 'CONTRACT_MISMATCH' }
      );
    }

    return {
      requestId: body.requestId,
      noWasteDetected: false,
      errorMessage: null,
      detectedType: body.detectedType,
      confidenceScore: body.confidenceScore,
      estimatedVolumeLiter: body.estimatedVolumeLiter,
      organikPercent: body.organik_percent,
      nonOrganikPercent: body.non_organik_percent,
      detections: body.detections || [],
      vendorName: body.vendorName ?? null,
      annotatedImageBase64: body.annotatedImageBase64,
      serverLatencyMs: body.serverLatencyMs ?? null,
    };
  }

  /** @private */
  async _fetchWithTimeout(url, fetchOptions) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      return await fetch(url, { ...fetchOptions, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }
}

module.exports = { FastApiWasteAiAdapter };
