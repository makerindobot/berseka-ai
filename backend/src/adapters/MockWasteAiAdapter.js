'use strict';
/**
 * MockWasteAiAdapter — implementasi IWasteAiAdapter untuk testing backend
 * TANPA butuh model serving FastAPI sungguhan berjalan (Backlog 7).
 *
 * Berguna untuk unit test route/business-logic backend Node.js yang tidak
 * seharusnya bergantung pada proses Python terpisah — deterministik &
 * cepat, beda tujuan dari MockClassifier Python (Backlog 6) yang mensimulasikan
 * variasi realistis model AI.
 */

const { IWasteAiAdapter } = require('./IWasteAiAdapter');

class MockWasteAiAdapter extends IWasteAiAdapter {
  /**
   * @param {object} [opts]
   * @param {boolean} [opts.forceNoWasteDetected] - jika true, semua
   *   panggilan analyzeImage() mengembalikan noWasteDetected:true (untuk
   *   menguji path error di backend).
   * @param {WasteAiPredictionResult} [opts.fixedResult] - override penuh
   *   hasil yang dikembalikan (untuk skenario test spesifik).
   */
  constructor({ forceNoWasteDetected = false, fixedResult = null } = {}) {
    super();
    this.forceNoWasteDetected = forceNoWasteDetected;
    this.fixedResult = fixedResult;
    this.calls = [];
  }

  get adapterName() {
    return 'mock-adapter';
  }

  async healthCheck() {
    return { ok: true, detail: { status: 'ok', model: 'mock-adapter' } };
  }

  async analyzeImage(imageBuffer, options = {}) {
    this.calls.push({ imageSize: imageBuffer?.length ?? 0, options });

    if (this.fixedResult) {
      return this.fixedResult;
    }

    if (this.forceNoWasteDetected) {
      return {
        requestId: `mock-${this.calls.length}`,
        noWasteDetected: true,
        errorMessage: 'Tidak ada sampah yang terdeteksi (mock adapter, forced).',
        detectedType: null,
        confidenceScore: null,
        estimatedVolumeLiter: null,
        organikPercent: null,
        nonOrganikPercent: null,
        detections: [],
        vendorName: null,
        annotatedImageBase64: null,
        serverLatencyMs: 1.23,
      };
    }

    return {
      requestId: `mock-${this.calls.length}`,
      noWasteDetected: false,
      errorMessage: null,
      detectedType: 'ORGANIC',
      confidenceScore: 0.87,
      estimatedVolumeLiter: 5.5,
      organikPercent: 80,
      nonOrganikPercent: 20,
      detections: [
        {
          label: 'ORGANIC',
          confidence: 0.87,
          bbox: { x_center: 0.5, y_center: 0.5, width: 0.2, height: 0.2 },
        },
      ],
      vendorName: options.vendorId || null,
      annotatedImageBase64: 'data:image/jpeg;base64,MOCK==',
      serverLatencyMs: 1.23,
    };
  }
}

module.exports = { MockWasteAiAdapter };
