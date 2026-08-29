# BERSEKA AI — Keputusan Kurasi Dataset (Backlog 1)

| | |
|---|---|
| **Proyek** | BERSEKA AI — Sistem Monitoring Kepatuhan Pemilahan Sampah, Kec. Coblong (kerja sama UNIKOM) |
| **Dokumen** | `docs/dataset/dataset-decision.md` |
| **Disusun oleh** | Dimas — Backend/ML Engineer, Damaker Studio |
| **Status** | Final — siap eksekusi Backlog 2 (akuisisi & preprocessing data) |
| **Target metrik model** | mAP@0.5 ≥ 0.85, akurasi klasifikasi ≥ 90%, F1-score ≥ 0.85, gap val–train loss ≤ 15% |

---

## 1. Ringkasan Eksekutif

Model BERSEKA AI butuh dua kapabilitas dalam satu pipeline: **deteksi objek** (bounding box tiap item sampah + estimasi volume) dan **klasifikasi biner** (ORGANIC vs NON_ORGANIC) untuk menghitung persentase komposisi per foto. Tidak ada satu dataset publik pun yang menyediakan keduanya sekaligus dengan skema label yang sudah sesuai kebutuhan kita (bbox + biner organik/anorganik + sudut pandang atas tong sampah). Karena itu strategi yang diambil adalah **kombinasi multi-dataset dengan label re-mapping**, bukan memilih satu dataset tunggal.

Keputusan inti:
- **Backbone deteksi**: TACO (kombinasi `vencerlanz09/taco-dataset-yolo-format` sebagai basis training cepat + `kneroma/tacotrashdataset` sebagai sumber verifikasi anotasi asli COCO) → dipetakan dari kelas granular ke 2 kelas target.
- **Penambah volume & keseimbangan kelas klasifikasi**: `sumn2u/garbage-classification-v2`, `alistairking/recyclable-and-household-waste-classification`, `joebeachcapital/realwaste`, dan `aashidutt3/waste-segregation-image-dataset` digunakan untuk memperkuat **classifier organik/anorganik** dan sebagai sumber tambahan crop untuk pretraining/augmentasi background, bukan sumber utama bounding box (karena mayoritas hanya berlabel classification, foto objek tunggal studio-style).
- Referensi implementasi: notebook `arshnoor7389/taco-to-yolo-waste-detection-with-yolov8` dipakai sebagai starting point pipeline konversi TACO→YOLO, **bukan** dipakai apa adanya — perlu diaudit ulang mapping kelasnya karena repo publik semacam ini umumnya memetakan ke kelas multi (litter/plastic/dll), bukan ke skema biner ORGANIC/NON_ORGANIC yang kita butuhkan.

---

## 2. Analisis Dataset Kandidat

### 2.1 `vencerlanz09/taco-dataset-yolo-format`
- **Isi**: TACO (Trash Annotations in Context) dikonversi ke format YOLO (txt bbox + images).
- **Sumber asli**: TACO dataset (Proença & Simões, 2020), 1500 foto asli, **9.823 objek anotasi** di **60 kelas granular** (mis. `Clear plastic bottle`, `Other plastic wrapper`, `Cigarette`, `Drink can`, `Broken glass`, `Paper cup`, `Styrofoam piece`, dll). Sering di-*group* menjadi 28 supercategory oleh publikasi turunan.
- **Anotasi**: Bounding box + polygon segmentation (versi asli COCO), sudah dikonversi ke bbox YOLO di versi ini. Kualitas anotasi tinggi (manual, dari studi akademik, dipakai luas di literatur).
- **Kekuatan**: Sudah dalam format siap-pakai untuk YOLOv5/v8, foto "waste in the wild" (jalanan, pantai, hutan, area urban) — variasi latar sangat tinggi, relevan untuk generalisasi model terhadap kondisi lapangan.
- **Kelemahan**: Ukuran dataset kecil (1500 foto) untuk skala deep learning modern, distribusi kelas **sangat timpang** (`cigarette` 1336 instance vs banyak kelas <50 instance/long-tail), sudut pandang foto TIDAK konsisten "tampak atas tong sampah" (mayoritas litter di tanah/alam terbuka, bukan di dalam tong) → ada **domain gap** dengan use-case BERSEKA yang perlu dimitigasi lewat fine-tuning tambahan atau capture data lapangan real di Backlog selanjutnya.
- **Lisensi**: Dataset asli TACO dirilis di bawah **CC BY 4.0** (bebas dipakai/dimodifikasi dengan atribusi) — dikonfirmasi dari repo resmi `pedropro/TACO` dan tacodataset.org. Reupload Kaggle mewarisi lisensi yang sama, atribusi ke paper TACO (Proença & Simões, 2020) wajib dicantumkan di dokumentasi model.

### 2.2 `kneroma/tacotrashdataset`
- **Isi**: TACO asli format COCO (JSON annotations + images), 15.635+ downloads.
- **Fungsi dalam strategi kami**: Dipakai sebagai **sumber verifikasi ground-truth** — karena versi YOLO (2.1) adalah hasil konversi pihak ketiga, kita cross-check jumlah objek/kelas terhadap file COCO asli untuk memastikan tidak ada bbox yang corrupt/hilang saat konversi format. Tidak dipakai langsung untuk training (redundan dengan 2.1 setelah convert ulang sendiri bila perlu presisi lebih tinggi, dengan skrip konversi yang kita audit sendiri, bukan asumsi hasil pihak ketiga).
- **Lisensi**: Sama, CC BY 4.0 (TACO asli).

### 2.3 `sumn2u/garbage-classification-v2`
- **Isi**: ~19.762–20.000 gambar (klaim README project turunan 19.762; deskripsi dataset publik menyebut hingga 20k dengan update berkelanjutan), **10 kelas**: metal, glass, biological, paper, battery, trash, cardboard, shoes, clothes, plastic.
- **Anotasi**: **Classification-only** (folder-per-kelas), TIDAK ada bounding box.
- **Kekuatan**: Volume besar, variasi foto cukup baik (bukan studio-only), kelas `biological` eksplisit tersedia untuk sisi ORGANIC.
- **Kelemahan**: Tidak ada bbox → tidak bisa dipakai langsung untuk training detector; hanya cocok untuk classifier / untuk sumber crop-and-paste synthetic bbox (lihat §4.3 strategi augmentasi).
- **Lisensi**: Perlu verifikasi manual di halaman Kaggle saat akuisisi (Backlog 2) — dataset publik non-institusional semacam ini di Kaggle umumnya CC0/CC BY/Community Data License; versi Roboflow turunan dari dataset serupa tercatat **CC BY 4.0**. **Catatan risiko**: dataset ini juga tersedia dalam bentuk berlapis (mengandung subset dari dataset lain seperti TrashNet & Garbage Classification asli) — wajib dicek ulang lisensi tiap sumber turunan sebelum publikasi model, karena proyek ini untuk client universitas dan butuh kepatuhan lisensi yang defensible.

### 2.4 `alistairking/recyclable-and-household-waste-classification`
- **Isi**: 15.000 gambar, resolusi seragam 256×256, **30 kelas** material/objek (mis. plastic bottle, aluminium can, cardboard box, food waste, glass bottle, styrofoam cup, paper cup, dll), tiap kelas punya 2 sub-set foto: `default` (studio/background bersih) dan `real_world` (kondisi nyata) — 250 gambar masing-masing = 500/kelas.
- **Anotasi**: Classification-only, tidak ada bbox.
- **Kekuatan**: Kelas granular & seimbang secara desain (500/kelas rata, tidak long-tail), memiliki subset `real_world` yang bagus untuk melatih ketahanan model terhadap variasi pencahayaan/background nyata — cocok dipakai sebagai **sumber augmentasi domain untuk classifier** dan pretraining backbone.
- **Kelemahan**: Resolusi rendah (256×256) membatasi kegunaannya untuk deteksi objek kecil; tidak ada anotasi organik/anorganik langsung — wajib mapping.
- **Lisensi**: Dinyatakan penulis untuk **"educational, research, atau non-commercial purposes"** (istilah dataset card, mirip CC BY-NC). **Implikasi penting**: karena BERSEKA AI adalah layanan ke warga (bukan riset murni) tapi berbasis kerja sama akademik dengan UNIKOM (bukan komersial-jual), dataset ini **aman dipakai untuk riset & pengembangan model dalam konteks kerja sama universitas**, namun PM/legal Damaker Studio perlu konfirmasi tertulis ke pemilik dataset bila produk akhir nanti dikomersialkan di luar konteks kerja sama akademik ini.

### 2.5 `aashidutt3/waste-segregation-image-dataset`
- **Isi**: Dataset klasifikasi biner eksplisit **Biodegradable vs Non-Biodegradable** — skema label ini paling dekat secara konsep dengan target ORGANIC/NON_ORGANIC BERSEKA.
- **Anotasi**: Classification-only, 2 kelas, tanpa bbox.
- **Kekuatan**: Tidak perlu re-mapping label sama sekali (mapping 1:1 Biodegradable→ORGANIC, Non-Biodegradable→NON_ORGANIC), langsung menambah data untuk classifier biner final.
- **Kelemahan**: Ukuran dataset relatif kecil dan sumber/detail metadata (jumlah pasti gambar, kondisi foto, lisensi eksplisit) kurang terdokumentasi publik dibanding dataset besar lain — perlu inspeksi manual isi dataset & README di Kaggle sebelum ditarik ke pipeline (Backlog 2) sebagai bagian due-diligence.
- **Lisensi**: Belum ada informasi eksplisit yang terverifikasi via pencarian publik → **wajib dicek langsung di halaman dataset (tab "Usability"/license badge) saat akuisisi**, jangan diasumsikan bebas pakai.

### 2.6 `joebeachcapital/realwaste`
- **Isi**: 4.752–4.808 gambar real, diambil di fasilitas pengolahan sampah nyata (Whyte's Gully, Wollongong, Australia) — bukan foto studio. **9 kelas**: Cardboard (461), Food Organics (411), Glass (420), Metal (790), Miscellaneous Trash (495), Paper (500), Plastic (921), Textile Trash (318), Vegetation (436), resolusi 524×524.
- **Anotasi**: Classification-only, tanpa bbox.
- **Kekuatan**: **Kualitas domain-realism tertinggi di antara semua kandidat** — item saling bertumpuk/campur (comingled), terkena kotoran, terdeformasi seperti kondisi sampah nyata di tong/TPS. Paper akademik terkait (Single et al., 2023, *Information* MDPI, DOI 10.3390/info14120633) melaporkan akurasi klasifikasi 85–89% dengan model CNN standar, dan secara eksplisit membuktikan model yang dilatih dari foto objek "pristine" (studio) turun jauh (≈49%) saat diuji pada foto kondisi nyata — **temuan ini jadi justifikasi kuat bagi keputusan kami untuk tidak mengandalkan dataset studio-only saja** (lihat §4.3 & §5).
- **Kelemahan**: Volume lebih kecil dari kandidat lain, kelas `Food Organics` & `Vegetation` perlu digabung jadi ORGANIC, sisanya NON_ORGANIC (Miscellaneous Trash perlu judgment call, lihat §3).
- **Lisensi — PERLU MITIGASI**: **Terdapat inkonsistensi lisensi antar sumber resmi.** UCI ML Repository mencantumkan **CC BY 4.0**, sementara IEEE DataPort mencantumkan **CC BY-NC-SA 4.0** (non-commercial, share-alike) untuk dataset yang sama. Keputusan mitigasi: **perlakukan dataset ini sebagai CC BY-NC-SA 4.0 (klausul paling ketat)** sampai tim legal/PM mengonfirmasi versi otoritatif ke penulis asli (Sarah Singh et al., University of Wollongong) — aman dipakai untuk riset/kerja sama akademik UNIKOM, tapi flag risiko bila BERSEKA AI dikomersialkan.

### 2.7 Notebook referensi `arshnoor7389/taco-to-yolo-waste-detection-with-yolov8`
- **Fungsi**: Referensi teknis untuk pipeline konversi anotasi TACO (COCO polygon) → format YOLO bbox, termasuk skrip *remapping* 60 kelas asli TACO ke sejumlah *supercategory* yang lebih sedikit.
- **Keputusan pemakaian**: Dipakai sebagai **starting point kode**, bukan output/model jadi. Mapping kelas di notebook publik ini didesain untuk tujuan riset penulis (bukan skema biner organik/anorganik kita) sehingga **tabel mapping kelas HARUS ditulis ulang sendiri** sesuai §3 di bawah, dan hasil konversi bbox harus diverifikasi ulang manual pada sample (spot-check ≥50 gambar per kelas mayor) sebelum dipakai untuk training — standar due-diligence sebelum reuse kode pihak ketiga.

### 2.8 Ringkasan Tabel Perbandingan

| Dataset | Jml Gambar (approx) | Jml Kelas Asli | Punya BBox? | Fungsi dalam Pipeline | Lisensi | Catatan Risiko |
|---|---|---|---|---|---|---|
| TACO YOLO (vencerlanz09) | 1.500 foto / 9.823 obj | 60 (granular) | ✅ Ya (YOLO txt) | **Basis detector** | CC BY 4.0 | Long-tail, sudut foto "in the wild" ≠ tampak atas tong |
| TACO COCO (kneroma) | 1.500 foto / 9.823 obj | 60 | ✅ Ya (COCO json) | Verifikasi ground-truth | CC BY 4.0 | Redundan dgn di atas, dipakai u/ QA anotasi |
| Garbage Classification v2 (sumn2u) | ~19.7k–20k | 10 | ❌ Tidak | Classifier + crop augmentasi | Perlu verifikasi ulang saat akuisisi | Dataset turunan berlapis, cek lisensi sumber asal |
| Recyclable & Household Waste (alistairking) | 15.000 | 30 | ❌ Tidak | Classifier + domain augmentasi (real_world subset) | Non-commercial/riset | Resolusi 256×256 rendah u/ deteksi |
| Waste Segregation (aashidutt3) | Belum terverifikasi jumlah pasti | 2 (Biodeg/Non-Biodeg) | ❌ Tidak | Classifier biner langsung (mapping 1:1) | **Belum terverifikasi** — cek saat akuisisi | Metadata publik minim |
| RealWaste (joebeachcapital) | 4.752–4.808 | 9 | ❌ Tidak | Classifier — domain-realism tertinggi | **CC BY-NC-SA 4.0** (ambil klausul terketat) | Konflik lisensi antar sumber, perlu konfirmasi resmi |

---

## 3. Skema Mapping Label: Granular → ORGANIC / NON_ORGANIC

Prinsip mapping: **ORGANIC** = sampah yang dapat terbiodegradasi secara alami (sisa makanan, tumbuhan/daun, kayu tak-olahan). **NON_ORGANIC** = seluruh sisanya (plastik, logam, kaca, kertas/kardus **terkontaminasi cetakan/laminasi**, tekstil, karet, kaca, baterai, B3, dll) — mengikuti definisi operasional pemilahan 2-bin yang dipakai program Kecamatan Coblong/UNIKOM (organik vs non-organik, bukan skema 3-4 kategori seperti TPS3R).

### 3.1 Mapping kelas TACO (60 kelas → 2 kelas)

| Kelas asal TACO (contoh, subset dari 60) | Target BERSEKA |
|---|---|
| Food waste, Banana peel/organic residue (bila ada di TACO sbg *Food waste*), *Garden waste* (jika muncul) | **ORGANIC** |
| Clear plastic bottle, Other plastic bottle, Plastic bottle cap, Plastic lid, Plastic film, Plastic straw, Plastic utensils, Disposable plastic cup, Styrofoam piece, Other plastic, Other plastic wrapper, Single-use carrier bag, Six pack rings | **NON_ORGANIC** |
| Drink can, Metal bottle cap, Aluminium foil, Scrap metal, Pop tab | **NON_ORGANIC** |
| Glass bottle, Glass jar, Glass cup, Broken glass | **NON_ORGANIC** |
| Normal paper, Paper cup, Paper bag, Tissues, Magazine paper, Wrapping paper, Corrugated carton, Other carton, Egg carton, Drink carton, Meal carton, Pizza box | **NON_ORGANIC** *(kertas terpakai/terlaminasi/berminyak → dianggap non-organik operasional; kertas & kardus TIDAK dianggap kompos-ready dalam program kota, konsisten dgn definisi Coblong 2-bin)* |
| Cigarette, Cigarette butt | **NON_ORGANIC** (filter mengandung plastik) |
| Rope & strings, Shoe, Squeezable tube, Plastic gloves | **NON_ORGANIC** |
| Battery | **NON_ORGANIC** (flag khusus B3 opsional untuk versi mendatang, di luar scope biner v1) |
| Unlabeled litter, Other litter | **DIBUANG dari training set** (ambigu, tidak bisa dipetakan aman ke salah satu kelas — lihat §3.3) |

> **Catatan penting**: TACO **tidak** punya kelas "sisa makanan/organik" yang kaya — kategori biological/food waste minim representasinya di TACO (dataset ini dominan litter non-organik jalanan). Ini adalah **alasan utama** kenapa dataset classifier tambahan (RealWaste, Garbage Classification v2, Waste Segregation, Alistairking) mutlak diperlukan: mereka menyumbang mayoritas sample kelas ORGANIC yang representatif (food, biological, vegetation).

### 3.2 Mapping kelas dataset classifier lain

| Dataset | Kelas asal | Target |
|---|---|---|
| RealWaste | Food Organics, Vegetation | ORGANIC |
| RealWaste | Cardboard, Glass, Metal, Paper, Plastic, Textile Trash | NON_ORGANIC |
| RealWaste | Miscellaneous Trash | NON_ORGANIC (default aman; item campuran umumnya non-organik dominan) |
| Garbage Classification v2 | biological | ORGANIC |
| Garbage Classification v2 | metal, glass, paper, battery, trash, cardboard, shoes, clothes, plastic | NON_ORGANIC |
| Alistairking (30 kelas) | food_waste, coffee_grounds, eggshells, tea_bags (jika ada di taksonomi 30 kelas — verifikasi nama pasti saat akuisisi) | ORGANIC |
| Alistairking (30 kelas) | seluruh kelas material (plastic bottle, aluminium can, cardboard box, glass jar, styrofoam cup, paper cup, dll) | NON_ORGANIC |
| Waste Segregation (aashidutt3) | Biodegradable | ORGANIC |
| Waste Segregation (aashidutt3) | Non-Biodegradable | NON_ORGANIC |

### 3.3 Aturan penanganan kelas ambigu/ditolak
1. **Kelas campuran/tidak jelas** (`Other litter`, `Unlabeled litter`, `Miscellaneous Trash` dengan visual campuran ekstrem) → **tidak dipakai untuk melatih classifier** (dibuang dari training set, boleh disisakan sebagian kecil di test set murni untuk mengukur *failure mode* model secara sadar).
2. **Kertas & kardus**: diperlakukan NON_ORGANIC secara konsisten di semua dataset sumber (walau secara material bisa terkompos, program Coblong dua-bin memperlakukannya sebagai non-organik operasional — dikonfirmasi dengan PM/klien sebelum lock final; jika klien punya definisi berbeda, mapping ini tinggal diubah di satu file `label_mapping.yaml` terpusat, bukan hardcode di kode training).
3. **Baterai/B3**: dipetakan NON_ORGANIC untuk v1 biner, namun ditandai `flag_hazard: true` di metadata dataset internal agar versi model berikutnya (jika scope diperluas ke 3+ kelas) tidak perlu re-anotasi dari nol.
4. Seluruh keputusan mapping ditulis di **satu file konfigurasi terpusat** (`configs/label_mapping.yaml`, dibuat di Backlog 2) — bukan tersebar di kode — agar auditable dan mudah direvisi bila definisi organik/anorganik klien berubah.

---

## 4. Strategi Kombinasi Dataset

### 4.1 Peran tiap dataset dalam pipeline

| Tahap | Dataset | Tujuan |
|---|---|---|
| **Detector (bbox) pretraining** | TACO (YOLO format), diverifikasi via TACO COCO | Melatih model mendeteksi *keberadaan & lokasi* objek sampah dalam foto |
| **Detector fine-tuning kelas 2-label** | TACO dgn label di-remap ke ORGANIC/NON_ORGANIC (§3.1) | Menyesuaikan output head detector ke skema biner target |
| **Classifier crop-level (2nd stage / auxiliary)** | Garbage Classification v2, Alistairking, RealWaste, Waste Segregation | Memperkaya variasi visual per kelas biner, terutama ORGANIC yang under-represented di TACO |
| **Volume/area estimation calibration** | Subset internal (difoto tim/warga uji coba, di luar dataset publik — dicatat sbg gap Backlog 2) | Bounding box area × kalibrasi jarak kamera → estimasi liter (dataset publik generik TIDAK menyediakan ground-truth volume liter — **wajib capture data kalibrasi lapangan sendiri**, direkomendasikan minimal 200–300 foto tong dgn known-volume markers) |

### 4.2 Strategi penyeimbangan kelas (class balancing)
- Distribusi awal (perkiraan gabungan dataset) akan **timpang ke NON_ORGANIC** (mayoritas dataset publik waste didominasi recyclables/plastic/metal/glass, sedangkan foto sisa makanan/organik lebih sedikit dan lebih cepat rusak/kurang difoto orang).
- Mitigasi:
  1. **Undersampling** kelas NON_ORGANIC dari dataset besar (Garbage Classification v2, Alistairking) agar rasio akhir mendekati 55:45 atau 60:40 (NON_ORGANIC sedikit lebih besar tetap wajar karena realistis di lapangan, tapi tidak boleh >70:30).
  2. **Oversampling + augmentasi berat** untuk kelas ORGANIC dari RealWaste (Food Organics + Vegetation, ±847 gambar asli) dan Garbage Classification v2 (`biological`), dikalikan augmentasi (§4.3) untuk mencapai target volume setara.
  3. Class weight / focal loss di level training (Backlog 2) sebagai mitigasi tambahan on-top data-level balancing, bukan pengganti.
- Target akhir kasar (indikatif, difinalisasi setelah Backlog 2 EDA nyata): ≥8.000 sample per kelas untuk classifier, ≥3.000 instance bbox per kelas untuk detector — angka ini dipilih berdasarkan rule-of-thumb transfer learning YOLO/CNN modern (ribuan, bukan ratusan, instance/kelas) mengingat target mAP 0.85 cukup ketat.

### 4.3 Strategi variasi kondisi foto (anti-overfitting terhadap homogenitas)
Risiko terbesar: model dilatih dominan dari foto **studio/background bersih single-object** (Alistairking `default` subset, sebagian Garbage Classification v2) sehingga gagal generalisasi ke foto **tampak-atas-tong-sampah** dunia nyata yang gelap, ramai, miring, dan diambil kamera HP murah warga. Studi RealWaste (Single et al. 2023) membuktikan empiris penurunan akurasi dari ~89% ke ~49% pada kasus serupa (model dilatih data pristine, diuji data real) — jadi ini bukan risiko teoretis.

Mitigasi:
1. **Prioritaskan subset "real_world" & "in the wild"**: pakai subset `real_world` Alistairking, seluruh RealWaste (memang dari fasilitas pengolahan nyata), dan seluruh TACO (foto lapangan) sebagai porsi dominan; subset studio-bersih (`default` Alistairking) dibatasi maksimal 25–30% dari total training set classifier agar tidak mendominasi distribusi.
2. **Domain randomization via augmentasi** (diterapkan di Backlog 2 dengan Albumentations/YOLO built-in aug):
   - Perspective/affine transform acak (simulasi sudut jepret tidak konsisten tampak-atas)
   - Brightness/contrast/gamma jitter luas (simulasi pencahayaan indoor buruk, backlight, malam hari dgn flash HP)
   - Motion blur & gaussian blur ringan-sedang (simulasi foto buram tangan gemetar)
   - Gaussian noise & JPEG compression artifact (simulasi kompresi WhatsApp/aplikasi mobile — foto warga sering dikirim via kompresi lossy)
   - Random crop/zoom + occlusion (cutout) parsial (simulasi tong sebagian tertutup tutup/tangan/bayangan)
   - Color jitter/hue shift moderat (variasi white-balance kamera HP berbeda-beda)
   - **Mosaic & mixup** (bawaan YOLOv8) khusus untuk detector, membantu model belajar konteks multi-objek tumpang tindih seperti isi tong sampah asli
   - Background compositing/copy-paste: crop objek dari dataset classification (tanpa bbox) ditempel ke background foto tong sampah kosong/random untuk membentuk sample bbox sintetik tambahan bagi kelas yang kurang di TACO (khususnya organik) — teknik ini yang membuat dataset classification tanpa bbox tetap bisa berkontribusi ke detector.
3. **Capture data lapangan asli** (di luar dataset publik, direkomendasikan sbg bagian awal Backlog 2): sesi foto pilot bersama beberapa RT/RW di Coblong, minimal 300–500 foto tong sampah asli tampak-atas dgn HP warga sungguhan, dijadikan **held-out real-world validation set** — ini krusial karena tidak ada dataset publik yang punya sudut pandang "tampak atas tong sampah" secara spesifik; performa di validation set ini adalah sinyal paling jujur soal kesiapan model untuk deployment, bukan sekadar metrik di test-set dataset publik.

---

## 5. Strategi Split Train/Val/Test

### 5.1 Rasio
- **70% Train / 15% Validation / 15% Test**, distratifikasi per kelas (ORGANIC/NON_ORGANIC) dan, untuk detector, juga per dataset-sumber (agar val/test tidak didominasi satu sumber saja).
- Rasio 70/15/15 dipilih (bukan 80/10/10) karena target mAP≥0.85 & F1≥0.85 memerlukan validation & test set yang cukup besar secara statistik untuk estimasi metrik yang stabil, mengingat kita mengombinasikan banyak sumber heterogen — 10% terlalu kecil untuk mendeteksi overfitting per-sumber secara reliable.

### 5.2 Anti-data-leakage — aturan wajib
1. **Split di level gambar sumber asli, sebelum augmentasi.** Augmentasi/oversampling HANYA diterapkan pada partisi *train* setelah split ditentukan — tidak pernah ada augmented copy dari gambar test/val yang bocor ke train, dan sebaliknya.
2. **Split per grup (group-aware), bukan per-gambar acak murni**, untuk dataset yang punya multiple foto dari kejadian/session yang sama (mis. TACO kadang punya beberapa foto sudut berbeda dari 1 lokasi litter yang sama; RealWaste diambil dalam sesi audit yang sama per hari) — seluruh foto dari 1 "grup/kejadian" HARUS berada di partisi yang sama (semua di train, atau semua di val, atau semua di test), memakai `GroupShuffleSplit` (scikit-learn) berbasis metadata lokasi/timestamp bila tersedia di masing-masing dataset.
3. **Stratifikasi ganda**: stratify by (label biner ORGANIC/NON_ORGANIC) DAN (dataset asal), supaya test set tetap merepresentasikan proporsi tiap sumber dataset, bukan kebetulan semua dari 1 dataset saja.
4. **Held-out real-world set terpisah total** (§4.3 poin 3): foto lapangan asli Kecamatan Coblong tidak ikut proses split random di atas — 100% dialokasikan sebagai final acceptance test, tidak pernah dilihat model selama training/validation, dipakai sebagai gerbang go/no-go sebelum deployment produksi.
5. **Deduplikasi lintas dataset** sebelum split: sejumlah dataset publik waste diketahui saling tumpang tindih/derivatif satu sama lain (mis. Garbage Classification v2 disebut berisi elemen dari dataset TrashNet/Garbage Classification lama — lihat catatan risiko §2.3). Wajib jalankan **perceptual hashing (pHash/dHash)** lintas seluruh dataset gabungan sebelum split final, buang duplikat/near-duplikat, agar sample yang "kelihatan" ada di train dan test sebenarnya tidak identik gambar yang sama — ini sumber kebocoran data yang sangat umum dan mudah luput ketika menggabungkan >1 dataset publik.
6. Proses split dijalankan dengan **random seed tetap** dan dicatat (`configs/split_seed.txt` / experiment tracking) agar reproducible dan bisa diaudit klien/akademik.

### 5.3 Verifikasi anti-overfitting sesuai target metrik
- Val loss dipantau tiap epoch vs train loss; deviasi >15% dari target adalah **stop criteria** (early stopping + checkpoint terbaik), bukan hanya dilaporkan di akhir.
- Karena data gabungan dari banyak sumber heterogen (mengurangi risiko homogenitas), plus held-out real-world Coblong set yang sepenuhnya independen, gap performa train↔val↔real-world test menjadi indikator utama generalisasi — bukan hanya angka val loss di dalam distribusi dataset publik.

---

## 6. Lisensi & Kepatuhan — Ringkasan Tindakan

| Dataset | Status Lisensi | Tindakan Wajib Sebelum Backlog 2 dieksekusi |
|---|---|---|
| TACO (kedua varian) | CC BY 4.0 — jelas, aman | Cantumkan sitasi paper TACO (Proença & Simões, 2020) di dokumentasi model |
| Garbage Classification v2 | Belum terverifikasi presisi, indikasi CC BY/CC0 turunan | Cek halaman Kaggle "Usability"/license badge saat akuisisi; telusuri provenance dataset turunan |
| Alistairking Recyclable & Household | Non-commercial/riset (dataset card) | Aman untuk kerja sama akademik UNIKOM; flag untuk review legal bila produk dikomersialkan |
| Waste Segregation (aashidutt3) | **Belum terverifikasi** | WAJIB cek lisensi eksplisit di halaman dataset sebelum ditarik ke pipeline |
| RealWaste | **Konflik**: CC BY 4.0 (UCI) vs CC BY-NC-SA 4.0 (IEEE DataPort) | Perlakukan sbg CC BY-NC-SA (klausul terketat) sampai ada konfirmasi resmi; aman untuk riset akademik, flag untuk komersialisasi |

**Rekomendasi ke PM**: karena BERSEKA AI berjalan dalam kerja sama akademik dengan UNIKOM (bukan produk komersial dijual bebas), seluruh dataset di atas **aman digunakan untuk fase riset & pengembangan model saat ini**. Namun sebelum model dirilis sebagai layanan publik/komersial di luar konteks kerja sama ini, item lisensi bertanda "perlu verifikasi/konflik" di atas harus dituntaskan status hukumnya oleh tim legal.

---

## 7. Gap & Rekomendasi Tindak Lanjut (untuk Backlog 2)

1. **Tidak ada dataset publik dengan ground-truth volume liter** — wajib bangun subset kalibrasi volume sendiri (foto tong dengan objek referensi ukuran diketahui) sebelum modul estimasi volume bisa dilatih/divalidasi dengan baik.
2. **Tidak ada dataset publik dengan sudut pandang "tampak atas tong sampah" secara spesifik** — capture pilot lapangan Kecamatan Coblong adalah prioritas tinggi, idealnya dimulai paralel dengan proses training model dari dataset publik (bukan menunggu model publik selesai dulu).
3. **🔴 GAP KRITIKAL — Representasi geografis/budaya sampah Indonesia (ditemukan 28 Agustus 2026, feedback Daffa).** Keenam dataset publik yang dipakai (§2) **TIDAK SATU PUN bersumber dari Indonesia**: TACO dominan Eropa (studi akademik Portugal + crowdsource global), RealWaste dari Wollongong Australia, sisanya (Garbage Classification v2, Alistairking, Waste Segregation) kompilasi Kaggle umum dengan foto studio/stock image yang didominasi konteks Barat/internasional. Implikasi nyata untuk BERSEKA:
   - **Sampah organik**: dataset publik dominan apel/kentang/sayur Barat — TIDAK merepresentasikan kulit durian/rambutan/pisang/kelapa, sisa nasi, daun pisang pembungkus yang jadi mayoritas sampah organik rumah tangga Indonesia. Tekstur, warna, dan bentuk berbeda signifikan.
   - **Sampah anorganik**: pola sampah plastik Indonesia punya karakter khas — **sachet plastik** (sampo/deterjen/kopi sachet, sangat umum di sini) dan **kresek** (kantong plastik tipis) — jarang direpresentasikan di dataset Barat yang lebih dominan botol/kaleng ukuran retail besar. Kemasan brand lokal (mis. Indomie) juga tidak ada di dataset manapun.
   - **Risiko produksi**: model berpotensi punya bias visual kuat ke arah "sampah gaya Barat" dan akurasinya bisa jatuh signifikan saat diuji di lapangan Coblong nyata — ini risiko akurasi produksi yang konkret, BUKAN cuma gap sudut kamera yang sudah dicatat di poin 2.
   - **Mitigasi yang SUDAH direncanakan tapi belum efektif**: capture data lapangan Coblong via bot Telegram (§7 poin 2 di atas, `field-data-collection-plan.md`) adalah SATU-SATUNYA sumber data yang bisa menutup gap representasi geografis ini sekaligus gap sudut pandang kamera. **Status per 28 Agustus 2026, 17:00 WIB: 0 foto terkumpul dari 32 kelompok KKN** — gap ini karena itu BUKAN cuma soal akurasi, tapi **blocker jalur kritis** yang makin mendesak. Rekomendasi: PM/Daffa perlu follow-up aktif ke koordinator (Pak Agus) untuk mempercepat partisipasi mahasiswa, bukan menunggu pasif.
   - **Mitigasi tambahan yang perlu dipertimbangkan** (di luar scope Backlog 1, untuk didiskusikan di Backlog 2/5): riset dataset publik tambahan yang lebih representatif Asia Tenggara/Indonesia (jika ada), atau pertimbangkan data augmentation terarah pada kelas organik untuk mensimulasikan variasi bentuk yang lebih luas — tapi keduanya TIDAK menggantikan kebutuhan data lapangan asli.
   - **Hasil riset tambahan (28 Agustus 2026)**: dicari dataset publik waste classification khusus Indonesia — **tidak ditemukan dataset foto siap-pakai**. Beberapa jurnal akademik Indonesia (mis. UIN Suka, UPN Yogyakarta, Universitas Mulia) meneliti klasifikasi sampah organik/anorganik, TAPI semuanya ternyata memakai dataset Kaggle generik yang sama (bukan foto sampah Indonesia asli) — mengonfirmasi tidak ada jalan pintas dataset publik untuk gap ini. **Data lapangan Coblong via bot Telegram BENAR-BENAR satu-satunya sumber data representatif Indonesia yang tersedia untuk proyek ini**, bukan cuma pilihan yang lebih disukai.
4. Sebelum konversi TACO→YOLO final dipakai, jalankan **spot-check manual** terhadap ≥50 sample per kelas mayor untuk memastikan hasil konversi bbox (dari `vencerlanz09` maupun reproduksi sendiri dari `kneroma` COCO) akurat, karena repo pihak ketiga rawan bug mapping koordinat/kelas.
5. Finalisasi ambang keputusan kelas abu-abu (kertas/kardus, miscellaneous trash) bersama PM & klien (UNIKOM/Kecamatan Coblong) sebelum lock `configs/label_mapping.yaml` — dokumen ini memberi rekomendasi teknis, tapi definisi operasional organik/non-organik adalah keputusan bisnis/kebijakan yang perlu sign-off klien.
6. Jalankan deduplikasi lintas-dataset (pHash) dan audit lisensi final sebagai gate wajib sebelum data dianggap "clean" untuk training.

---

*Dokumen ini adalah keputusan teknis Backlog 1 dan menjadi acuan bagi implementasi akuisisi & preprocessing data di Backlog 2. Setiap perubahan skema mapping label atau strategi split wajib diperbarui di sini agar tetap menjadi single source of truth yang auditable.*
