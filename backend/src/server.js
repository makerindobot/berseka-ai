'use strict';
/**
 * BERSEKA AI — Backend Node.js entrypoint (Backlog 7).
 *
 * Menjalankan lokal (dev):
 *   WASTE_AI_ADAPTER=fastapi WASTE_AI_API_BASE_URL=http://127.0.0.1:8000 \
 *     node src/server.js
 *
 * Atau pakai mock adapter (tanpa butuh FastAPI berjalan):
 *   WASTE_AI_ADAPTER=mock node src/server.js
 */

require('dotenv').config();

const express = require('express');
const path = require('node:path');

const { openDatabase } = require('./db/schema');
const { ScanRepository } = require('./db/scanRepository');
const { createWasteAiAdapter } = require('./adapters/createWasteAiAdapter');
const { createScanRouter } = require('./routes/scan');

function createApp({ wasteAiAdapter, db } = {}) {
  const app = express();
  app.use(express.json());

  const resolvedAdapter = wasteAiAdapter || createWasteAiAdapter();
  const resolvedDb = db || openDatabase(process.env.SCAN_DB_PATH || path.join(__dirname, '../data/scans.db'));
  const scanRepository = new ScanRepository(resolvedDb);
  const scanWindows = scanRepository.getScanWindows();

  app.get('/healthz', async (req, res) => {
    const aiHealth = await resolvedAdapter.healthCheck();
    res.json({
      status: aiHealth.ok ? 'ok' : 'degraded',
      adapter: resolvedAdapter.adapterName,
      aiHealth,
    });
  });

  app.use(createScanRouter({ wasteAiAdapter: resolvedAdapter, scanRepository, scanWindows }));

  return { app, db: resolvedDb, scanRepository, wasteAiAdapter: resolvedAdapter };
}

if (require.main === module) {
  const { app } = createApp();
  const port = Number(process.env.PORT || 4000);
  app.listen(port, () => {
    console.log(`BERSEKA backend listening on port ${port} (adapter=${process.env.WASTE_AI_ADAPTER || 'fastapi'})`);
  });
}

module.exports = { createApp };
