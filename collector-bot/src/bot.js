'use strict';
/**
 * bot.js — BERSEKA AI Collector Bot
 *
 * =============================================================================
 * SENGAJA TERISOLASI TOTAL DARI CLAUDE CODE / GATEWAY CONTROL PLANE
 * =============================================================================
 * Ini adalah proses Node.js MANDIRI, dijalankan lewat systemd service-nya
 * sendiri (berseka-collector-bot.service), BUKAN bagian dari hermes-gateway
 * / 9router.service yang berjalan di VPS yang sama.
 *
 * Kemampuan bot ini SENGAJA dibatasi hanya ke 4 hal:
 *   1. Menerima command Telegram (/mulai) & tap tombol inline keyboard.
 *   2. Menerima file foto dari user Telegram.
 *   3. Meng-upload foto ke storage (Cloudflare R2 atau fallback lokal).
 *   4. Menyimpan metadata ke file JSONL lokal.
 *
 * Bot ini SECARA SENGAJA TIDAK PUNYA:
 *   - Kemampuan eksekusi command sistem / akses shell (tidak ada child_process,
 *     tidak ada exec/spawn di seluruh source tree collector-bot/).
 *   - Kemampuan memanggil API Hermes atau MCP tool apa pun.
 *   - Jalur relay pesan dari user Telegram ke Claude Code / asisten AI mana pun.
 *   - Port inbound (pakai long polling Telegram, bukan webhook) - tidak perlu
 *     buka port baru di firewall/UFW VPS.
 *
 * Jika kelak ada kebutuhan menambah fitur, developer WAJIB mempertahankan
 * batasan ini kecuali ada keputusan eksplisit & terdokumentasi dari pemilik
 * proyek (Daffa) untuk mengubah model keamanan ini. Lihat juga README.md
 * bagian "Security & Isolation".
 * =============================================================================
 */

const TelegramBot = require('node-telegram-bot-api');
const { loadConfig } = require('./lib/config');
const { createStorage } = require('./lib/storage');
const { ManifestWriter, TARGET_PER_GROUP_PER_TYPE } = require('./lib/manifest');

const JENIS_TONG = {
  organik: { label: 'Organik', emoji: '🟢' },
  anorganik: { label: 'Anorganik', emoji: '🔵' },
};

// In-memory session state per chat. Bot ini stateless terhadap sistem lain -
// state hanya menyimpan progres wizard (kelompok dipilih, jenis tong dipilih)
// dan hilang begitu proses restart. Tidak ada data sensitif di sini.
const sessions = new Map();

function getSession(chatId) {
  if (!sessions.has(chatId)) {
    sessions.set(chatId, {});
  }
  return sessions.get(chatId);
}

function chunkGroupsIntoRows(groups, perRow = 2) {
  const rows = [];
  for (let i = 0; i < groups.length; i += perRow) {
    const row = groups.slice(i, i + perRow).map((g) => ({
      text: g.label,
      callback_data: `group:${g.id}`,
    }));
    rows.push(row);
  }
  return rows;
}

function jenisTongKeyboard() {
  return {
    inline_keyboard: [
      [
        { text: `${JENIS_TONG.organik.emoji} ${JENIS_TONG.organik.label}`, callback_data: 'jenis:organik' },
        { text: `${JENIS_TONG.anorganik.emoji} ${JENIS_TONG.anorganik.label}`, callback_data: 'jenis:anorganik' },
      ],
    ],
  };
}

function main() {
  const config = loadConfig();
  const storage = createStorage(config);
  const manifest = new ManifestWriter({ manifestPath: config.manifestPath });

  const bot = new TelegramBot(config.botToken, { polling: true });

  console.log('[berseka-collector-bot] Bot dimulai (long polling). Mode storage:', config.storageMode);
  console.log('[berseka-collector-bot] Jumlah kelompok terdaftar:', config.groups.length);

  bot.onText(/^\/start$|^\/mulai$/, (msg) => {
    const chatId = msg.chat.id;
    sessions.set(chatId, {});
    const rows = chunkGroupsIntoRows(config.groups);
    bot.sendMessage(
      chatId,
      '👋 Halo! Selamat datang di *Bot Pengumpul Foto BERSEKA AI*.\n\n' +
        'Silakan pilih nomor kelompok kalian:',
      { reply_markup: { inline_keyboard: rows }, parse_mode: 'Markdown' }
    );
  });

  bot.onText(/^\/progress$/, (msg) => {
    const chatId = msg.chat.id;
    const summary = manifest.getProgressSummaryAll ? manifest.getProgressSummaryAll() : manifest.getProgress();
    if (!summary || Object.keys(summary).length === 0) {
      bot.sendMessage(
        chatId,
        '📊 *Progress Pengumpulan Foto BERSEKA AI*\n\n' +
          'Belum ada data yang terkumpul.',
        { parse_mode: 'Markdown' }
      );
      return;
    }

    let text = '📊 *Progress Pengumpulan Foto BERSEKA AI*\n' +
      `Target per kelompok: ${TARGET_PER_GROUP_PER_TYPE} organik + ${TARGET_PER_GROUP_PER_TYPE} anorganik = ${TARGET_PER_GROUP_PER_TYPE * 2} total\n\n`;

    // Urutkan berdasarkan total (descending)
    const sorted = Object.values(summary).sort((a, b) => b.total - a.total);

    for (const group of sorted) {
      const orgPct = Math.round((group.organik / TARGET_PER_GROUP_PER_TYPE) * 100);
      const anorgPct = Math.round((group.anorganik / TARGET_PER_GROUP_PER_TYPE) * 100);
      const totalPct = Math.round((group.total / (TARGET_PER_GROUP_PER_TYPE * 2)) * 100);

      const progressBar = (pct) => {
        const filled = Math.min(Math.round(pct / 10), 10);
        return '█'.repeat(filled) + '░'.repeat(10 - filled) + ` ${pct}%`;
      };

      text += `*${group.groupLabel}*\n`;
      text += `  🟢 Organik: ${group.organik}/${TARGET_PER_GROUP_PER_TYPE} ${progressBar(orgPct)}\n`;
      text += `  🔵 Anorganik: ${group.anorganik}/${TARGET_PER_GROUP_PER_TYPE} ${progressBar(anorgPct)}\n`;
      text += `  📦 Total: ${group.total}/${TARGET_PER_GROUP_PER_TYPE * 2} (${totalPct}%)\n\n`;
    }

    // Ringkasan keseluruhan
    const allOrg = Object.values(summary).reduce((sum, g) => sum + g.organik, 0);
    const allAnorg = Object.values(summary).reduce((sum, g) => sum + g.anorganik, 0);
    const allTotal = allOrg + allAnorg;
    const allGroups = Object.keys(summary).length;

    text += `---\n`;
    text += `📈 *Ringkasan Keseluruhan*\n`;
    text += `Kelompok aktif: ${allGroups}/32\n`;
    text += `Total foto: ${allTotal}/${32 * TARGET_PER_GROUP_PER_TYPE * 2} (${Math.round((allTotal / (32 * TARGET_PER_GROUP_PER_TYPE * 2)) * 100)}%)\n`;
    text += `🟢 Organik: ${allOrg} | 🔵 Anorganik: ${allAnorg}`;

    bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
  });

  bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const data = query.data || '';
    const session = getSession(chatId);

    try {
      if (data.startsWith('group:')) {
        const groupId = data.split(':').slice(1).join(':');
        const group = config.groups.find((g) => g.id === groupId);
        if (!group) {
          await bot.answerCallbackQuery(query.id, { text: 'Kelompok tidak valid.' });
          return;
        }
        session.groupId = group.id;
        session.groupLabel = group.label;
        await bot.answerCallbackQuery(query.id);
        await bot.sendMessage(
          chatId,
          `✅ Kelompok dipilih: *${group.label}*\n\nSekarang pilih jenis tong sampah yang mau difoto:`,
          { reply_markup: jenisTongKeyboard(), parse_mode: 'Markdown' }
        );
        return;
      }

      if (data.startsWith('jenis:')) {
        const jenis = data.split(':')[1];
        if (!JENIS_TONG[jenis]) {
          await bot.answerCallbackQuery(query.id, { text: 'Pilihan tidak valid.' });
          return;
        }
        if (!session.groupId) {
          await bot.answerCallbackQuery(query.id, { text: 'Silakan pilih kelompok dulu dengan /mulai.' });
          return;
        }
        session.jenisTong = jenis;
        await bot.answerCallbackQuery(query.id);
        await bot.sendMessage(
          chatId,
          `📸 Jenis tong: *${JENIS_TONG[jenis].label}*\n\n` +
            'Sekarang kirim foto tong sampahnya (foto dari atas, jelas & cukup cahaya).',
          { parse_mode: 'Markdown' }
        );
        return;
      }

      await bot.answerCallbackQuery(query.id);
    } catch (err) {
      console.error('[berseka-collector-bot] Error handling callback_query:', err);
      try {
        await bot.answerCallbackQuery(query.id, { text: 'Terjadi kesalahan, coba lagi.' });
      } catch (_) {
        /* noop */
      }
    }
  });

  bot.on('photo', async (msg) => {
    const chatId = msg.chat.id;
    const session = getSession(chatId);

    if (!session.groupId || !session.jenisTong) {
      await bot.sendMessage(
        chatId,
        '⚠️ Sebelum kirim foto, silakan ketik /mulai lalu pilih kelompok dan jenis tong dulu ya.'
      );
      return;
    }

    try {
      // Ambil resolusi foto terbesar yang dikirim Telegram.
      const photos = msg.photo;
      const best = photos[photos.length - 1];
      const fileId = best.file_id;

      const fileLink = await bot.getFileLink(fileId);
      const response = await fetch(fileLink);
      if (!response.ok) {
        throw new Error(`Gagal mengunduh foto dari Telegram: HTTP ${response.status}`);
      }
      const arrayBuffer = await response.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      const timestampIso = new Date().toISOString();
      // Format tampilan untuk pesan ke user: WIB (UTC+7) eksplisit, BUKAN
      // ISO/UTC mentah - mahasiswa awam bisa salah kira jam UTC = jam lokal
      // (insiden nyata 28 Agustus 2026: PM sempat salah lapor "07:37 WIB"
      // padahal itu 07:37 UTC = 14:37 WIB, karena label zona waktu tidak
      // eksplisit). timestamp_iso (UTC) TETAP disimpan apa adanya di
      // manifest untuk konsistensi data/audit - hanya tampilan ke user
      // yang dikonversi ke WIB.
      const timestampWibDisplay = new Intl.DateTimeFormat('id-ID', {
        timeZone: 'Asia/Jakarta',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }).format(new Date(timestampIso));

      const result = await storage.putPhoto({
        buffer,
        groupId: session.groupId,
        jenisTong: session.jenisTong,
        timestampIso,
      });

      const metadata = {
        kelompok_id: session.groupId,
        kelompok_label: session.groupLabel,
        jenis_tong: session.jenisTong,
        timestamp_iso: timestampIso,
        // telegram_user_id disimpan HANYA untuk audit teknis internal
        // (mis. debugging duplikasi/spam), BUKAN untuk identifikasi
        // pribadi ke publik atau dipublikasikan bersama dataset.
        telegram_user_id: msg.from ? msg.from.id : null,
        file_id: fileId,
        storage_mode: result.storageMode,
        storage_key: result.key,
        storage_location: result.location,
      };

      manifest.append(metadata);

      // Generate progress summary untuk balasan otomatis
      const progress = manifest.getProgressSummary(session.groupId);

      await bot.sendMessage(
        chatId,
        `✅ Foto tersimpan!\n\n` +
          `Kelompok: *${session.groupLabel}*\n` +
          `Jenis: *${JENIS_TONG[session.jenisTong].label}*\n` +
          `Waktu: ${timestampWibDisplay} WIB\n\n` +
          `📊 *Progress ${session.groupLabel}*\n` +
          `🟢 Organik: ${progress.organik.count}/${TARGET_PER_GROUP_PER_TYPE} ${progress.organik.bar}\n` +
          `🔵 Anorganik: ${progress.anorganik.count}/${TARGET_PER_GROUP_PER_TYPE} ${progress.anorganik.bar}\n` +
          `📦 Total: ${progress.total.count}/${TARGET_PER_GROUP_PER_TYPE * 2} (${progress.total.pct}%)\n\n` +
          'Boleh kirim foto lagi (jenis tong yang sama), atau ketik /mulai untuk ganti kelompok/jenis, atau /progress untuk lihat semua kelompok.',
        { parse_mode: 'Markdown' }
      );
    } catch (err) {
      console.error('[berseka-collector-bot] Error handling photo:', err);
      await bot.sendMessage(
        chatId,
        '❌ Maaf, ada kendala saat menyimpan foto. Coba kirim ulang, atau hubungi koordinator jika terus gagal.'
      );
    }
  });

  bot.on('polling_error', (err) => {
    console.error('[berseka-collector-bot] Polling error:', err.message || err);
  });

  process.on('SIGTERM', () => {
    console.log('[berseka-collector-bot] SIGTERM diterima, berhenti dengan baik...');
    bot.stopPolling().finally(() => process.exit(0));
  });
  process.on('SIGINT', () => {
    console.log('[berseka-collector-bot] SIGINT diterima, berhenti dengan baik...');
    bot.stopPolling().finally(() => process.exit(0));
  });
}

main();
