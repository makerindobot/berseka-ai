"""
BERSEKA AI — Mock/Stub Classifier Service (Backlog 6).

// TODO: replace dengan model YOLOv8 hasil training Backlog 5

Kelas `MockClassifier` di sini SENGAJA dibuat dengan interface (method
signature & bentuk return) yang mensimulasikan apa yang akan dikembalikan
model YOLOv8 asli nanti (`src/training/train.py` + inference wrapper),
sehingga saat Backlog 5 selesai, `routes/predict.py` dan `routes/ws_predict.py`
tinggal ganti pemanggilan `MockClassifier().predict(...)` menjadi
`RealYoloClassifier().predict(...)` TANPA mengubah struktur/skema response.

Strategi mock (bukan model asli, jelas didokumentasikan agar tidak
disalahartikan):
1. Analisis warna dominan gambar (heuristik sederhana: rasio channel hijau
   vs channel lain) untuk membuat mock classifier "sadar konten" alih-alih
   pure random murni — mendekati perilaku classifier organik (hijau/coklat
   dominan) vs non-organik (warna lain/metalik/plastik cerah) tanpa benar-benar
   melakukan computer vision sesungguhnya.
2. Random jitter ditambahkan di atas heuristik warna supaya variasi confidence
   & bbox terasa realistis untuk keperluan uji integrasi FE/BE (bukan selalu
   angka yang sama).
3. Delay buatan (artificial processing time) mensimulasikan latency inference
   model CV sungguhan (beberapa puluh-ratus ms), supaya kode pemanggil
   (routes, WebSocket, load-test) sudah terbiasa dengan pola async/latency
   nyata sebelum model asli di-plug-in.
"""

from __future__ import annotations

import asyncio
import io
import random
import time
from dataclasses import dataclass, field
from typing import List

from PIL import Image

from api.schemas.predict_schema import BoundingBox, Detection, DetectedType

# Ambang confidence minimum sesuai kontrak Backlog 4:
# "Validasi confidence < 40% -> error NO_WASTE_DETECTED"
CONFIDENCE_THRESHOLD = 0.40

# Rentang delay buatan (detik) yang mensimulasikan waktu inference model
# CV sungguhan di CPU/GPU kelas menengah — dipakai supaya struktur async
# & pengukuran latency sudah teruji realistis sebelum model asli masuk.
_MOCK_MIN_LATENCY_S = 0.05
_MOCK_MAX_LATENCY_S = 0.18


@dataclass
class MockPrediction:
    """Struktur hasil internal mock classifier, sebelum dipetakan ke
    Pydantic response schema oleh route handler. Bentuk ini meniru apa
    yang akan dikembalikan wrapper inference YOLOv8 asli nanti."""

    detected_type: DetectedType
    confidence_score: float
    estimated_volume_liter: float
    organik_percent: float
    non_organik_percent: float
    detections: List[Detection] = field(default_factory=list)
    vendor_name: str | None = None


class MockClassifier:
    """// TODO: replace dengan model YOLOv8 hasil training Backlog 5

    Interface `predict_async(image_bytes)` dipertahankan identik dengan
    yang direncanakan untuk wrapper model asli, supaya swap implementasi
    di routes/*.py cukup ganti 1 baris import/instantiation.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    # -- heuristik "sadar konten" sangat sederhana, BUKAN computer vision asli --
    def _dominant_channel_bias(self, image_bytes: bytes) -> float:
        """Menghitung bias sederhana berbasis warna dominan gambar:
        mengembalikan nilai 0.0-1.0, makin tinggi makin condong ke
        "hijau/coklat" (proxy kasar untuk organik). Ini BUKAN model ML,
        murni statistik pixel rata-rata untuk membuat mock terasa
        kontekstual, bukan pure random.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_small = img.resize((32, 32))
            pixels = list(img_small.getdata())
            n = len(pixels)
            if n == 0:
                return 0.5
            avg_r = sum(p[0] for p in pixels) / n
            avg_g = sum(p[1] for p in pixels) / n
            avg_b = sum(p[2] for p in pixels) / n
            # Hijau/coklat dominan (g tinggi relatif, atau r&g tinggi b rendah -> coklat)
            greenish = avg_g - max(avg_r, avg_b)
            brownish = (avg_r + avg_g) / 2 - avg_b
            raw_bias = max(greenish, brownish * 0.5)
            # normalize kasar ke 0..1
            normalized = 0.5 + (raw_bias / 255.0)
            return max(0.0, min(1.0, normalized))
        except Exception:
            # Gambar tidak bisa dibaca PIL (mis. corrupt) -> netral, biar
            # logic threshold confidence di atas yang menangani penolakan.
            return 0.5

    def _generate_detections(self, dominant_type: DetectedType, count: int) -> List[Detection]:
        detections = []
        for _ in range(count):
            conf = round(self._rng.uniform(0.35, 0.98), 4)
            label = dominant_type
            # sesekali selipkan label sebaliknya agar `detections[]` terasa
            # realistis (foto sering berisi campuran objek)
            if self._rng.random() < 0.25:
                label = (
                    DetectedType.NON_ORGANIC
                    if dominant_type == DetectedType.ORGANIC
                    else DetectedType.ORGANIC
                )
            bbox = BoundingBox(
                x_center=round(self._rng.uniform(0.15, 0.85), 4),
                y_center=round(self._rng.uniform(0.15, 0.85), 4),
                width=round(self._rng.uniform(0.05, 0.35), 4),
                height=round(self._rng.uniform(0.05, 0.35), 4),
            )
            detections.append(Detection(label=label, confidence=conf, bbox=bbox))
        return detections

    def predict_sync(self, image_bytes: bytes) -> MockPrediction:
        """Simulasi inference sinkron (dipakai internal oleh predict_async
        setelah delay buatan). // TODO: replace dengan model YOLOv8 asli."""

        bias = self._dominant_channel_bias(image_bytes)
        # confidence keseluruhan: campuran bias konten + random jitter,
        # supaya kadang jatuh di bawah threshold (memicu NO_WASTE_DETECTED)
        # -- ini SENGAJA agar path error teruji, bukan bug.
        overall_confidence = round(
            max(0.0, min(1.0, self._rng.gauss(mu=0.55 + (bias - 0.5) * 0.3, sigma=0.22))), 4
        )

        organik_percent = round(bias * 100 * self._rng.uniform(0.85, 1.15), 2)
        organik_percent = max(0.0, min(100.0, organik_percent))
        non_organik_percent = round(100.0 - organik_percent, 2)

        detected_type = DetectedType.ORGANIC if bias >= 0.5 else DetectedType.NON_ORGANIC
        if 45.0 <= organik_percent <= 55.0:
            detected_type = DetectedType.MIXED

        num_detections = self._rng.randint(1, 5)
        detections = self._generate_detections(detected_type, num_detections)

        estimated_volume_liter = round(self._rng.uniform(0.5, 20.0), 2)

        return MockPrediction(
            detected_type=detected_type,
            confidence_score=overall_confidence,
            estimated_volume_liter=estimated_volume_liter,
            organik_percent=organik_percent,
            non_organik_percent=non_organik_percent,
            detections=detections,
            vendor_name=None,
        )

    async def predict_async(self, image_bytes: bytes) -> tuple[MockPrediction, float]:
        """Entry point async dipakai oleh routes/predict.py & ws_predict.py.

        Return: (MockPrediction, elapsed_ms) — elapsed_ms diukur nyata
        dengan time.perf_counter() (bukan hardcode), mencakup delay buatan
        + waktu heuristik warna, mensimulasikan latency inference model
        CV sungguhan.
        """
        start = time.perf_counter()

        # Delay buatan untuk mensimulasikan compute time inference nyata.
        artificial_delay = self._rng.uniform(_MOCK_MIN_LATENCY_S, _MOCK_MAX_LATENCY_S)
        await asyncio.sleep(artificial_delay)

        prediction = self.predict_sync(image_bytes)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return prediction, elapsed_ms
