'use strict';
/**
 * Validasi jadwal scan otomatis pagi/sore (Backlog 7 poin 4):
 * "sistem menentukan waktu pagi/sore" — logika ini menentukan window scan
 * mana yang sedang aktif berdasarkan waktu sekarang, dan apakah sebuah
 * waktu tertentu berada di dalam salah satu window terjadwal.
 */

function parseHHMM(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

/**
 * @param {Array<{window_name: string, start_time: string, end_time: string}>} windows
 * @param {Date} [now]
 * @returns {string} "pagi" | "sore" | "manual" (manual = di luar semua window terjadwal)
 */
function determineScanWindow(windows, now = new Date()) {
  const minutesNow = now.getHours() * 60 + now.getMinutes();
  for (const w of windows) {
    const start = parseHHMM(w.start_time);
    const end = parseHHMM(w.end_time);
    if (minutesNow >= start && minutesNow <= end) {
      return w.window_name;
    }
  }
  return 'manual';
}

/**
 * @param {Array<{window_name: string, start_time: string, end_time: string}>} windows
 * @param {string} windowName - "pagi" | "sore"
 * @param {Date} [now]
 * @returns {boolean}
 */
function isWithinScanWindow(windows, windowName, now = new Date()) {
  const target = windows.find((w) => w.window_name === windowName);
  if (!target) return false;
  const minutesNow = now.getHours() * 60 + now.getMinutes();
  return minutesNow >= parseHHMM(target.start_time) && minutesNow <= parseHHMM(target.end_time);
}

module.exports = { determineScanWindow, isWithinScanWindow, parseHHMM };
