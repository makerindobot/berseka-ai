'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');

const { determineScanWindow, isWithinScanWindow } = require('../src/lib/scanWindow');

const windows = [
  { window_name: 'pagi', start_time: '05:00', end_time: '09:00' },
  { window_name: 'sore', start_time: '15:00', end_time: '18:00' },
];

function atTime(hh, mm) {
  const d = new Date();
  d.setHours(hh, mm, 0, 0);
  return d;
}

test('determineScanWindow mengembalikan "pagi" jika dalam rentang pagi', () => {
  assert.equal(determineScanWindow(windows, atTime(6, 30)), 'pagi');
});

test('determineScanWindow mengembalikan "sore" jika dalam rentang sore', () => {
  assert.equal(determineScanWindow(windows, atTime(16, 0)), 'sore');
});

test('determineScanWindow mengembalikan "manual" di luar semua window', () => {
  assert.equal(determineScanWindow(windows, atTime(12, 0)), 'manual');
  assert.equal(determineScanWindow(windows, atTime(22, 0)), 'manual');
});

test('determineScanWindow batas tepat awal/akhir window inclusive', () => {
  assert.equal(determineScanWindow(windows, atTime(5, 0)), 'pagi');
  assert.equal(determineScanWindow(windows, atTime(9, 0)), 'pagi');
  assert.equal(determineScanWindow(windows, atTime(9, 1)), 'manual');
});

test('isWithinScanWindow konsisten dgn determineScanWindow', () => {
  assert.equal(isWithinScanWindow(windows, 'pagi', atTime(6, 0)), true);
  assert.equal(isWithinScanWindow(windows, 'sore', atTime(6, 0)), false);
  assert.equal(isWithinScanWindow(windows, 'pagi', atTime(20, 0)), false);
});
