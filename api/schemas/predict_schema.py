"""
BERSEKA AI — Pydantic schemas untuk kontrak API Model Serving (Backlog 6).

Kontrak field mengikuti persis dokumen kontrak yang sudah diberikan Daffa
dan direferensikan di:
  - docs/BACKLOG.md (QC 2, Backlog 4, Backlog 6)
  - docs/dataset/dataset-decision.md

Field response wajib (case-sensitive, JANGAN diubah tanpa sign-off Daffa):
  requestId, detectedType, confidenceScore, estimatedVolumeLiter,
  organik_percent, non_organik_percent, detections[], vendorName,
  annotatedImageBase64

Error response wajib memakai kode `NO_WASTE_DETECTED` ketika confidence
di bawah ambang (< 40%) atau tidak ada objek sampah yang terdeteksi sama
sekali.

Skema ini SENGAJA independen dari model AI yang dipakai di baliknya
(mock sekarang, YOLOv8 asli nanti / Backlog 5) — kontrak I/O API tidak
boleh berubah saat model asli di-swap in.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, confloat


class DetectedType(str, Enum):
    """Klasifikasi biner sesuai skema label final Backlog 1
    (docs/dataset/dataset-decision.md §3): ORGANIC vs NON_ORGANIC.
    MIXED dipakai ketika foto berisi campuran kedua jenis sampah."""

    ORGANIC = "ORGANIC"
    NON_ORGANIC = "NON_ORGANIC"
    MIXED = "MIXED"


class BoundingBox(BaseModel):
    """Koordinat bounding box ternormalisasi (0.0-1.0 relatif terhadap
    lebar/tinggi gambar), konsisten dengan format YOLO (x_center, y_center,
    width, height)."""

    x_center: confloat(ge=0.0, le=1.0) = Field(..., description="Titik tengah bbox sumbu X (normalized)")
    y_center: confloat(ge=0.0, le=1.0) = Field(..., description="Titik tengah bbox sumbu Y (normalized)")
    width: confloat(gt=0.0, le=1.0) = Field(..., description="Lebar bbox (normalized)")
    height: confloat(gt=0.0, le=1.0) = Field(..., description="Tinggi bbox (normalized)")


class Detection(BaseModel):
    """Satu item deteksi objek sampah di dalam foto (elemen `detections[]`)."""

    label: DetectedType = Field(..., description="Kelas hasil deteksi objek ini: ORGANIC / NON_ORGANIC")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence score deteksi objek ini (0.0-1.0)")
    bbox: BoundingBox = Field(..., description="Bounding box objek terdeteksi")


class PredictRequestMeta(BaseModel):
    """Metadata opsional yang menyertai multipart/form-data request /predict.
    Field `image` (UploadFile) sendiri dideklarasikan langsung di signature
    endpoint FastAPI (routes/predict.py), bukan lewat model ini, karena
    FastAPI multipart tidak mendukung file di dalam nested Pydantic model
    tanpa penanganan khusus."""

    vendorId: Optional[str] = Field(
        default=None,
        description="ID tong sampah / vendor pemindai (opsional, dipakai untuk kalibrasi/lookup vendorName)",
    )


class PredictResponse(BaseModel):
    """Skema response sukses untuk /predict (HTTP) dan /ws/predict (WebSocket).
    Field HARUS identik nama & tipe di kedua endpoint — WS menambahkan
    field `serverLatencyMs` di atas skema ini (lihat WsPredictResponse)."""

    requestId: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID unik request, dipakai untuk tracing/audit trail",
    )
    detectedType: DetectedType = Field(..., description="Klasifikasi dominan hasil deteksi: ORGANIC / NON_ORGANIC / MIXED")
    confidenceScore: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence score keseluruhan hasil deteksi (0.0-1.0)")
    estimatedVolumeLiter: confloat(ge=0.0) = Field(..., description="Estimasi volume sampah terdeteksi dalam liter")
    organik_percent: confloat(ge=0.0, le=100.0) = Field(..., description="Persentase komposisi sampah organik dalam foto")
    non_organik_percent: confloat(ge=0.0, le=100.0) = Field(..., description="Persentase komposisi sampah non-organik dalam foto")
    detections: List[Detection] = Field(default_factory=list, description="Daftar objek sampah individual yang terdeteksi")
    vendorName: Optional[str] = Field(default=None, description="Nama vendor/lokasi tong sampah, jika teridentifikasi")
    annotatedImageBase64: str = Field(..., description="Gambar hasil anotasi (bbox digambar) dalam base64, format data URI JPEG/PNG")


class WsPredictResponse(PredictResponse):
    """Response untuk WebSocket /ws/predict — identik dengan PredictResponse
    ditambah `serverLatencyMs` (waktu proses server, diukur nyata pakai
    time.perf_counter(), BUKAN hardcode)."""

    serverLatencyMs: float = Field(..., ge=0.0, description="Latency pemrosesan di server dalam milliseconds (diukur nyata)")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Kode error mesin-terbaca, mis. NO_WASTE_DETECTED")
    message: str = Field(..., description="Pesan error yang bisa ditampilkan ke pengguna")


class ErrorResponse(BaseModel):
    """Skema error response kontrak — dipakai ketika confidence < 40%
    (ambang sesuai Backlog 4) atau tidak ada objek sampah yang terdeteksi
    sama sekali."""

    requestId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    error: ErrorDetail


# Kode error kontrak — konstanta terpusat agar tidak ada typo tersebar di kode.
ERROR_NO_WASTE_DETECTED = "NO_WASTE_DETECTED"
