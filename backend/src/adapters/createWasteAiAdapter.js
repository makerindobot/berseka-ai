'use strict';
/**
 * Adapter factory — memilih implementasi IWasteAiAdapter berdasarkan env
 * var, supaya kode caller (routes/scan.js, dll) tidak perlu tahu detail
 * konstruksi adapter (Backlog 7).
 *
 * Env vars:
 *   WASTE_AI_ADAPTER        - "fastapi" (default) | "mock"
 *   WASTE_AI_API_BASE_URL   - wajib jika adapter=fastapi, mis.
 *                             "http://127.0.0.1:8000"
 *   WASTE_AI_TIMEOUT_MS     - opsional, default 15000
 */

const { FastApiWasteAiAdapter } = require('./FastApiWasteAiAdapter');
const { MockWasteAiAdapter } = require('./MockWasteAiAdapter');

function createWasteAiAdapter(env = process.env) {
  const kind = (env.WASTE_AI_ADAPTER || 'fastapi').toLowerCase();

  if (kind === 'mock') {
    return new MockWasteAiAdapter();
  }

  if (kind === 'fastapi') {
    return new FastApiWasteAiAdapter({
      baseUrl: env.WASTE_AI_API_BASE_URL,
      timeoutMs: env.WASTE_AI_TIMEOUT_MS ? Number(env.WASTE_AI_TIMEOUT_MS) : undefined,
    });
  }

  throw new Error(
    `WASTE_AI_ADAPTER='${kind}' tidak dikenal. Nilai valid: "fastapi" | "mock".`
  );
}

module.exports = { createWasteAiAdapter };
