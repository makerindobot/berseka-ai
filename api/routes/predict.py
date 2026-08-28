"""
BERSEKA AI — Endpoint POST /predict (HTTP, multipart/form-data) — Backlog 6.

// TODO: replace dengan model YOLOv8 hasil training Backlog 5
Saat ini pakai MockClassifier (api/services/mock_classifier.py) karena
model YOLOv8 asli masih menunggu dataset lapangan & training run GPU
(lihat docs/BACKLOG.md Backlog 5, docs/architecture/training-pipeline.md).

Kontrak:
  - Request: multipart/form-data, field `image` (file), field opsional
    `vendorId` (str).
  - Response sukses (200): PredictResponse (schemas/predict_schema.py)
  - Response gagal validasi confidence (200 dgn body error terstruktur,
    ATAU 422 tergantung kesepakatan FE — di sini kita pakai HTTP 200 body
    error terstruktur supaya klien mobile tidak perlu cabang khusus untuk
    status code non-2xx pada kasus bisnis "tidak ada sampah terdeteksi",
    konsisten dengan pola umum API computer-vision serving; endpoint tetap
    mengembalikan HTTP 422 murni untuk kesalahan validasi request itself
    (mis. file bukan gambar) via FastAPI default exception handling.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api.schemas.predict_schema import (
    ERROR_NO_WASTE_DETECTED,
    ErrorDetail,
    ErrorResponse,
    PredictResponse,
)
from api.services.image_annotator import draw_annotations_base64
from api.services.mock_classifier import CONFIDENCE_THRESHOLD, MockClassifier

logger = logging.getLogger("berseka.api.predict")

router = APIRouter()

# Instance tunggal (stateless mock, aman dipakai lintas request).
# // TODO: ganti dengan instance wrapper model YOLOv8 asli Backlog 5.
_classifier = MockClassifier()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


@router.post(
    "/predict",
    response_model=None,
    summary="Prediksi jenis & volume sampah dari 1 foto (mock classifier)",
)
async def predict(
    image: UploadFile = File(..., description="File gambar tong sampah (JPEG/PNG/WebP)"),
    vendorId: str | None = Form(default=None, description="ID vendor/tong sampah opsional"),
):
    if image.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Tipe file '{image.content_type}' tidak didukung. Gunakan JPEG/PNG/WebP.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="File gambar kosong / tidak terbaca.")

    prediction, elapsed_ms = await _classifier.predict_async(image_bytes)
    logger.info(
        "predict processed request vendorId=%s confidence=%.4f elapsed_ms=%.2f",
        vendorId,
        prediction.confidence_score,
        elapsed_ms,
    )

    if prediction.confidence_score < CONFIDENCE_THRESHOLD:
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=ERROR_NO_WASTE_DETECTED,
                message=(
                    "Tidak ada sampah yang terdeteksi dengan cukup yakin pada foto ini "
                    f"(confidence {prediction.confidence_score:.2f} < ambang {CONFIDENCE_THRESHOLD:.2f}). "
                    "Silakan foto ulang dengan pencahayaan lebih baik & jarak sesuai panduan."
                ),
            )
        )
        return JSONResponse(status_code=200, content=error_response.model_dump())

    annotated_b64 = draw_annotations_base64(image_bytes, prediction.detections)

    response = PredictResponse(
        detectedType=prediction.detected_type,
        confidenceScore=prediction.confidence_score,
        estimatedVolumeLiter=prediction.estimated_volume_liter,
        organik_percent=prediction.organik_percent,
        non_organik_percent=prediction.non_organik_percent,
        detections=prediction.detections,
        vendorName=vendorId,
        annotatedImageBase64=annotated_b64,
    )
    return response
