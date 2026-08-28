"""
BERSEKA AI — Endpoint WebSocket /ws/predict (realtime) — Backlog 6.

// TODO: replace dengan model YOLOv8 hasil training Backlog 5

Protokol:
  - Client connect ke `ws://<host>/ws/predict`.
  - Client mengirim FRAME BINARY (bytes gambar JPEG/PNG mentah) satu per
    pesan — bukan JSON/base64 — supaya cocok untuk streaming realtime dari
    kamera (menghindari overhead encoding base64 ~33% per frame).
  - Server membalas 1 pesan JSON per frame yang diterima, berisi field
    `WsPredictResponse` (identik `PredictResponse` + `serverLatencyMs`).
  - Jika confidence < ambang (`NO_WASTE_DETECTED`), server tetap membalas
    JSON (bukan menutup koneksi) berisi `ErrorResponse` — supaya klien bisa
    terus mengirim frame berikutnya tanpa reconnect.
  - Koneksi tetap terbuka sampai client disconnect (WebSocketDisconnect)
    atau client mengirim teks `"__close__"` (opsional, kemudahan testing
    manual via wscat/websocat tanpa perlu benar-benar kirim binary).
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.schemas.predict_schema import (
    ERROR_NO_WASTE_DETECTED,
    ErrorDetail,
    ErrorResponse,
    WsPredictResponse,
)
from api.services.image_annotator import draw_annotations_base64
from api.services.mock_classifier import CONFIDENCE_THRESHOLD, MockClassifier

logger = logging.getLogger("berseka.api.ws_predict")

router = APIRouter()

# Instance tunggal (stateless mock) — dipakai bersama predict.py agar
# perilaku HTTP & WS identik. // TODO: ganti wrapper model YOLOv8 asli.
_classifier = MockClassifier()

# Batas ukuran frame (bytes) untuk mencegah client nakal/bug mengirim
# payload raksasa yang membebani memori server mock (± 1.9GB RAM gateway,
# lihat memory note VPS) — nilai longgar untuk foto kamera HP wajar.
_MAX_FRAME_BYTES = 12 * 1024 * 1024  # 12 MB


@router.websocket("/ws/predict")
async def ws_predict(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("ws_predict connection accepted client=%s", websocket.client)

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            frame_bytes: bytes | None = message.get("bytes")
            frame_text: str | None = message.get("text")

            if frame_text is not None:
                if frame_text.strip() == "__close__":
                    await websocket.close(code=1000)
                    break
                # Teks selain sinyal close bukan bagian kontrak -> abaikan
                # dengan pesan error ringan, jangan putus koneksi.
                await websocket.send_json(
                    ErrorResponse(
                        error=ErrorDetail(
                            code="INVALID_FRAME_FORMAT",
                            message="Frame harus berupa binary image bytes, bukan teks.",
                        )
                    ).model_dump()
                )
                continue

            if frame_bytes is None:
                continue

            if len(frame_bytes) == 0:
                await websocket.send_json(
                    ErrorResponse(
                        error=ErrorDetail(
                            code="EMPTY_FRAME",
                            message="Frame gambar kosong diterima, frame diabaikan.",
                        )
                    ).model_dump()
                )
                continue

            if len(frame_bytes) > _MAX_FRAME_BYTES:
                await websocket.send_json(
                    ErrorResponse(
                        error=ErrorDetail(
                            code="FRAME_TOO_LARGE",
                            message=f"Frame melebihi batas {_MAX_FRAME_BYTES // (1024 * 1024)}MB.",
                        )
                    ).model_dump()
                )
                continue

            ws_start = time.perf_counter()
            prediction, _classifier_elapsed_ms = await _classifier.predict_async(frame_bytes)

            if prediction.confidence_score < CONFIDENCE_THRESHOLD:
                error_response = ErrorResponse(
                    error=ErrorDetail(
                        code=ERROR_NO_WASTE_DETECTED,
                        message=(
                            "Tidak ada sampah yang terdeteksi dengan cukup yakin pada frame ini "
                            f"(confidence {prediction.confidence_score:.2f} < ambang "
                            f"{CONFIDENCE_THRESHOLD:.2f})."
                        ),
                    )
                )
                await websocket.send_json(error_response.model_dump())
                continue

            annotated_b64 = draw_annotations_base64(frame_bytes, prediction.detections)
            server_latency_ms = (time.perf_counter() - ws_start) * 1000.0

            response = WsPredictResponse(
                detectedType=prediction.detected_type,
                confidenceScore=prediction.confidence_score,
                estimatedVolumeLiter=prediction.estimated_volume_liter,
                organik_percent=prediction.organik_percent,
                non_organik_percent=prediction.non_organik_percent,
                detections=prediction.detections,
                vendorName=None,
                annotatedImageBase64=annotated_b64,
                serverLatencyMs=round(server_latency_ms, 3),
            )
            await websocket.send_json(response.model_dump())

    except WebSocketDisconnect:
        logger.info("ws_predict client disconnected client=%s", websocket.client)
    except Exception:
        logger.exception("ws_predict unexpected error, closing connection")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
