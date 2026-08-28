'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');

const { DatabaseSync } = require('node:sqlite');
const { openDatabase } = require('../src/db/schema');
const { ScanRepository } = require('../src/db/scanRepository');

function makeInMemoryDb() {
  // openDatabase() jalankan migrate() otomatis; pakai path :memory: unik
  // per test file run supaya tidak bentrok antar test.
  return openDatabase(':memory:');
}

test('ScanRepository insertScan & getScanById round-trip sukses', () => {
  const db = makeInMemoryDb();
  const repo = new ScanRepository(db);

  const result = {
    requestId: 'req-1',
    noWasteDetected: false,
    errorMessage: null,
    detectedType: 'ORGANIC',
    confidenceScore: 0.91,
    estimatedVolumeLiter: 3.2,
    organikPercent: 70,
    nonOrganikPercent: 30,
    detections: [{ label: 'ORGANIC', confidence: 0.91, bbox: { x_center: 0.5, y_center: 0.5, width: 0.1, height: 0.1 } }],
    vendorName: 'TONG-01',
    annotatedImageBase64: 'data:image/jpeg;base64,AAA',
    serverLatencyMs: 12.3,
  };

  const id = repo.insertScan({
    requestId: result.requestId,
    vendorId: 'TONG-01',
    wargaId: 'warga-1',
    kelompokKknId: 'kelompok-1',
    scanWindow: 'pagi',
    result,
    adapterName: 'mock-adapter',
  });

  assert.ok(id > 0);

  const fetched = repo.getScanById(id);
  assert.equal(fetched.request_id, 'req-1');
  assert.equal(fetched.detected_type, 'ORGANIC');
  assert.equal(fetched.no_waste_detected, false);
  assert.equal(fetched.detections.length, 1);
  assert.equal(fetched.scan_window, 'pagi');
});

test('ScanRepository insertScan menyimpan hasil NO_WASTE_DETECTED dgn benar', () => {
  const db = makeInMemoryDb();
  const repo = new ScanRepository(db);

  const result = {
    requestId: 'req-2',
    noWasteDetected: true,
    errorMessage: 'Tidak ada sampah terdeteksi.',
    detectedType: null,
    confidenceScore: null,
    estimatedVolumeLiter: null,
    organikPercent: null,
    nonOrganikPercent: null,
    detections: [],
    vendorName: null,
    annotatedImageBase64: null,
    serverLatencyMs: 5.0,
  };

  const id = repo.insertScan({
    requestId: result.requestId,
    scanWindow: 'manual',
    result,
    adapterName: 'mock-adapter',
  });

  const fetched = repo.getScanById(id);
  assert.equal(fetched.no_waste_detected, true);
  assert.equal(fetched.error_message, 'Tidak ada sampah terdeteksi.');
  assert.equal(fetched.detected_type, null);
});

test('ScanRepository listScans filter by kelompokKknId', () => {
  const db = makeInMemoryDb();
  const repo = new ScanRepository(db);

  const baseResult = {
    requestId: 'req-x',
    noWasteDetected: false,
    errorMessage: null,
    detectedType: 'NON_ORGANIC',
    confidenceScore: 0.6,
    estimatedVolumeLiter: 1.0,
    organikPercent: 10,
    nonOrganikPercent: 90,
    detections: [],
    vendorName: null,
    annotatedImageBase64: null,
    serverLatencyMs: 1,
  };

  repo.insertScan({ requestId: 'a', kelompokKknId: 'k1', scanWindow: 'pagi', result: baseResult, adapterName: 'mock' });
  repo.insertScan({ requestId: 'b', kelompokKknId: 'k2', scanWindow: 'sore', result: baseResult, adapterName: 'mock' });
  repo.insertScan({ requestId: 'c', kelompokKknId: 'k1', scanWindow: 'sore', result: baseResult, adapterName: 'mock' });

  const k1Scans = repo.listScans({ kelompokKknId: 'k1' });
  assert.equal(k1Scans.length, 2);
  assert.ok(k1Scans.every((s) => s.kelompok_kkn_id === 'k1'));
});

test('ScanRepository getComplianceSummary hitung rata-rata organik_percent hanya dari scan valid', () => {
  const db = makeInMemoryDb();
  const repo = new ScanRepository(db);

  const validResult = (organik) => ({
    requestId: `req-${organik}`,
    noWasteDetected: false,
    errorMessage: null,
    detectedType: 'ORGANIC',
    confidenceScore: 0.8,
    estimatedVolumeLiter: 1.0,
    organikPercent: organik,
    nonOrganikPercent: 100 - organik,
    detections: [],
    vendorName: null,
    annotatedImageBase64: null,
    serverLatencyMs: 1,
  });

  const invalidResult = {
    requestId: 'req-invalid',
    noWasteDetected: true,
    errorMessage: 'no waste',
    detectedType: null,
    confidenceScore: null,
    estimatedVolumeLiter: null,
    organikPercent: null,
    nonOrganikPercent: null,
    detections: [],
    vendorName: null,
    annotatedImageBase64: null,
    serverLatencyMs: 1,
  };

  repo.insertScan({ requestId: 'req-60', kelompokKknId: 'k1', scanWindow: 'pagi', result: validResult(60), adapterName: 'mock' });
  repo.insertScan({ requestId: 'req-80', kelompokKknId: 'k1', scanWindow: 'sore', result: validResult(80), adapterName: 'mock' });
  repo.insertScan({ requestId: 'req-invalid', kelompokKknId: 'k1', scanWindow: 'manual', result: invalidResult, adapterName: 'mock' });

  const summary = repo.getComplianceSummary('k1');
  assert.equal(summary.totalScans, 3);
  assert.equal(summary.validScans, 2);
  assert.equal(summary.avgOrganikPercent, 70);
});

test('getScanWindows mengembalikan default pagi & sore', () => {
  const db = makeInMemoryDb();
  const repo = new ScanRepository(db);
  const windows = repo.getScanWindows();
  const names = windows.map((w) => w.window_name).sort();
  assert.deepEqual(names, ['pagi', 'sore']);
});
