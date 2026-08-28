'use strict';
/**
 * Route POST /api/scan — endpoint utama integrasi Backend Node.js dengan
 * model AI (Backlog 7 poin 1 & 2): terima foto dari klien (mis. web
 * dashboard atau aplikasi warga), panggil IWasteAiAdapter, simpan histori
 * ke DB, kembalikan hasil.
 *
 * TIDAK menerima file langsung dari Telegram bot (collector-bot) — bot itu
 * SENGAJA terisolasi (lihat collector-bot/src/bot.js) dan cuma untuk
 * pengumpulan data training, bukan alur scan produksi warga.
 */

const express = require('express');
const { determineScanWindow } = require('../lib/scanWindow');

/**
 * Body parser multipart minimal tanpa dependency tambahan (busboy/multer) -
 * proyek ini sudah menahan diri dari dependency Node yang tidak esensial
 * (lihat package.json: cuma express + dotenv). Kalau volume upload
 * bertambah kompleks di masa depan, pertimbangkan `multer` — untuk scope
 * Backlog 7 saat ini, satu file gambar per request cukup ditangani parser
 * bawaan `express.raw()` dengan Content-Type spesifik dari klien
 * (klien mengirim body mentah gambar, BUKAN multipart/form-data, untuk
 * menyederhanakan sisi backend; metadata dikirim lewat query string).
 *
 * Kontrak endpoint:
 *   POST /api/scan?vendorId=...&wargaId=...&kelompokKknId=...
 *   Content-Type: image/jpeg (atau image/png, image/webp)
 *   Body: raw bytes gambar
 */

function createScanRouter({ wasteAiAdapter, scanRepository, scanWindows }) {
  const router = express.Router();

  router.post(
    '/api/scan',
    express.raw({ type: ['image/jpeg', 'image/png', 'image/webp'], limit: '15mb' }),
    async (req, res) => {
      if (!Buffer.isBuffer(req.body) || req.body.length === 0) {
        return res.status(422).json({
          error: {
            code: 'INVALID_IMAGE_BODY',
            message:
              'Body request harus berupa bytes gambar mentah dengan Content-Type image/jpeg|png|webp.',
          },
        });
      }

      const { vendorId, wargaId, kelompokKknId } = req.query;
      const scanWindow = determineScanWindow(scanWindows, new Date());

      let result;
      try {
        result = await wasteAiAdapter.analyzeImage(req.body, {
          vendorId: typeof vendorId === 'string' ? vendorId : undefined,
          mimeType: req.headers['content-type'],
        });
      } catch (err) {
        req.log?.error?.(err);
        return res.status(502).json({
          error: {
            code: err.code || 'WASTE_AI_ADAPTER_ERROR',
            message: `Gagal menghubungi model AI: ${err.message}`,
          },
        });
      }

      let insertedId = null;
      try {
        insertedId = scanRepository.insertScan({
          requestId: result.requestId,
          vendorId: typeof vendorId === 'string' ? vendorId : undefined,
          wargaId: typeof wargaId === 'string' ? wargaId : undefined,
          kelompokKknId: typeof kelompokKknId === 'string' ? kelompokKknId : undefined,
          scanWindow,
          result,
          adapterName: wasteAiAdapter.adapterName,
        });
      } catch (err) {
        // Kegagalan simpan DB tidak boleh menyembunyikan hasil AI dari
        // klien (hasil analisis tetap valid) — dilog, direspons dgn flag,
        // TAPI tetap kembalikan 200 dgn hasil prediksi supaya UX tidak
        // rusak hanya karena masalah penyimpanan histori.
        req.log?.error?.(err);
      }

      if (result.noWasteDetected) {
        return res.status(200).json({
          requestId: result.requestId,
          scanId: insertedId,
          scanWindow,
          error: { code: 'NO_WASTE_DETECTED', message: result.errorMessage },
        });
      }

      return res.status(200).json({
        requestId: result.requestId,
        scanId: insertedId,
        scanWindow,
        detectedType: result.detectedType,
        confidenceScore: result.confidenceScore,
        estimatedVolumeLiter: result.estimatedVolumeLiter,
        organikPercent: result.organikPercent,
        nonOrganikPercent: result.nonOrganikPercent,
        detections: result.detections,
        vendorName: result.vendorName,
        annotatedImageBase64: result.annotatedImageBase64,
      });
    }
  );

  router.get('/api/scan/:id', (req, res) => {
    const scan = scanRepository.getScanById(Number(req.params.id));
    if (!scan) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Scan tidak ditemukan.' } });
    }
    return res.json(scan);
  });

  router.get('/api/scans', (req, res) => {
    const { vendorId, kelompokKknId, limit } = req.query;
    const scans = scanRepository.listScans({
      vendorId: typeof vendorId === 'string' ? vendorId : undefined,
      kelompokKknId: typeof kelompokKknId === 'string' ? kelompokKknId : undefined,
      limit: limit ? Number(limit) : undefined,
    });
    return res.json({ scans });
  });

  router.get('/api/compliance/:kelompokKknId', (req, res) => {
    const summary = scanRepository.getComplianceSummary(req.params.kelompokKknId);
    return res.json(summary);
  });

  return router;
}

module.exports = { createScanRouter };
