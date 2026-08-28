'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');

const { MockWasteAiAdapter } = require('../src/adapters/MockWasteAiAdapter');
const { openDatabase } = require('../src/db/schema');
const { createApp } = require('../src/server');

async function startTestServer(adapterOpts = {}) {
  const adapter = new MockWasteAiAdapter(adapterOpts);
  const db = openDatabase(':memory:');
  const { app } = createApp({ wasteAiAdapter: adapter, db });
  return { app, adapter };
}

function jpegBuffer() {
  // Header JPEG minimal (tidak perlu gambar valid penuh -- backend hanya
  // meneruskan bytes ke adapter, tidak mem-parsing gambar sendiri).
  return Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46]);
}

test('POST /api/scan sukses mengembalikan kontrak field & simpan ke DB', async () => {
  const { app } = await startTestServer();
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const resp = await fetch(`http://127.0.0.1:${port}/api/scan?vendorId=TONG-01&kelompokKknId=k1`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: jpegBuffer(),
    });
    assert.equal(resp.status, 200);
    const body = await resp.json();
    assert.ok(body.requestId);
    assert.ok(body.scanId > 0);
    assert.equal(body.scanWindow, 'manual'); // default scan_windows gak nyakup semua jam
    assert.equal(body.detectedType, 'ORGANIC');
    assert.equal(body.vendorName, 'TONG-01');
    assert.ok(Array.isArray(body.detections));

    // verifikasi tersimpan di DB via endpoint get
    const getResp = await fetch(`http://127.0.0.1:${port}/api/scan/${body.scanId}`);
    assert.equal(getResp.status, 200);
    const scanRow = await getResp.json();
    assert.equal(scanRow.request_id, body.requestId);
  } finally {
    server.close();
  }
});

test('POST /api/scan dgn adapter forceNoWasteDetected mengembalikan error kontrak', async () => {
  const { app } = await startTestServer({ forceNoWasteDetected: true });
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const resp = await fetch(`http://127.0.0.1:${port}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: jpegBuffer(),
    });
    assert.equal(resp.status, 200);
    const body = await resp.json();
    assert.equal(body.error.code, 'NO_WASTE_DETECTED');
  } finally {
    server.close();
  }
});

test('POST /api/scan menolak body kosong dgn 422', async () => {
  const { app } = await startTestServer();
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const resp = await fetch(`http://127.0.0.1:${port}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: Buffer.alloc(0),
    });
    assert.equal(resp.status, 422);
    const body = await resp.json();
    assert.equal(body.error.code, 'INVALID_IMAGE_BODY');
  } finally {
    server.close();
  }
});

test('GET /healthz melaporkan status adapter', async () => {
  const { app } = await startTestServer();
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const resp = await fetch(`http://127.0.0.1:${port}/healthz`);
    assert.equal(resp.status, 200);
    const body = await resp.json();
    assert.equal(body.status, 'ok');
    assert.equal(body.adapter, 'mock-adapter');
  } finally {
    server.close();
  }
});

test('GET /api/scans mendukung filter vendorId', async () => {
  const { app } = await startTestServer();
  const server = app.listen(0);
  const port = server.address().port;

  try {
    await fetch(`http://127.0.0.1:${port}/api/scan?vendorId=TONG-A`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: jpegBuffer(),
    });
    await fetch(`http://127.0.0.1:${port}/api/scan?vendorId=TONG-B`, {
      method: 'POST',
      headers: { 'Content-Type': 'image/jpeg' },
      body: jpegBuffer(),
    });

    const resp = await fetch(`http://127.0.0.1:${port}/api/scans?vendorId=TONG-A`);
    const body = await resp.json();
    assert.equal(body.scans.length, 1);
    assert.equal(body.scans[0].vendor_id, 'TONG-A');
  } finally {
    server.close();
  }
});
