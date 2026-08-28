"""Integration test untuk BERSEKA AI Model Serving API (Backlog 6).

Menguji kontrak endpoint /predict (HTTP) dan /ws/predict (WebSocket) memakai
TestClient FastAPI (starlette), tanpa perlu server sungguhan berjalan.
MockClassifier dipakai apa adanya (bukan di-mock ulang) supaya test ini juga
memverifikasi perilaku mock end-to-end (termasuk path NO_WASTE_DETECTED).
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from api.services.mock_classifier import CONFIDENCE_THRESHOLD

client = TestClient(app)


def _make_jpeg_bytes(color: tuple[int, int, int] = (34, 139, 34), size=(64, 64)) -> bytes:
    """Gambar solid-color kecil, valid sebagai JPEG asli (bukan sekadar bytes acak)."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_healthz_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_predict_http_returns_contract_fields():
    image_bytes = _make_jpeg_bytes(color=(34, 139, 34))  # hijau -> condong ORGANIC
    resp = client.post(
        "/predict",
        files={"image": ("test.jpg", image_bytes, "image/jpeg")},
        data={"vendorId": "TONG-001"},
    )
    assert resp.status_code == 200
    body = resp.json()

    # Kasus sukses ATAU kasus NO_WASTE_DETECTED, keduanya HTTP 200 (lihat docstring route).
    if "error" in body:
        assert body["error"]["code"] == "NO_WASTE_DETECTED"
        assert "requestId" in body
        return

    required_fields = {
        "requestId",
        "detectedType",
        "confidenceScore",
        "estimatedVolumeLiter",
        "organik_percent",
        "non_organik_percent",
        "detections",
        "vendorName",
        "annotatedImageBase64",
    }
    assert required_fields.issubset(body.keys())
    assert body["detectedType"] in {"ORGANIC", "NON_ORGANIC", "MIXED"}
    assert 0.0 <= body["confidenceScore"] <= 1.0
    assert body["vendorName"] == "TONG-001"
    assert body["annotatedImageBase64"].startswith("data:image/jpeg;base64,")

    # annotatedImageBase64 harus benar-benar decodable sebagai gambar valid.
    b64_data = body["annotatedImageBase64"].split(",", 1)[1]
    decoded = base64.b64decode(b64_data)
    Image.open(io.BytesIO(decoded)).verify()

    for det in body["detections"]:
        assert det["label"] in {"ORGANIC", "NON_ORGANIC", "MIXED"}
        assert 0.0 <= det["confidence"] <= 1.0
        bbox = det["bbox"]
        assert 0.0 <= bbox["x_center"] <= 1.0
        assert 0.0 <= bbox["y_center"] <= 1.0


def test_predict_http_rejects_unsupported_content_type():
    resp = client.post(
        "/predict",
        files={"image": ("test.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 422


def test_predict_http_rejects_empty_file():
    resp = client.post(
        "/predict",
        files={"image": ("test.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 422


def test_predict_many_requests_eventually_hits_no_waste_detected():
    """MockClassifier punya randomness -> kirim banyak request untuk
    memverifikasi path NO_WASTE_DETECTED benar-benar bisa terpicu
    (bukan cuma teori), sesuai kontrak Backlog 4."""
    image_bytes = _make_jpeg_bytes(color=(128, 128, 128))
    saw_error = False
    saw_success = False
    for _ in range(60):
        resp = client.post("/predict", files={"image": ("t.jpg", image_bytes, "image/jpeg")})
        assert resp.status_code == 200
        body = resp.json()
        if "error" in body:
            assert body["error"]["code"] == "NO_WASTE_DETECTED"
            saw_error = True
        else:
            assert body["confidenceScore"] >= CONFIDENCE_THRESHOLD
            saw_success = True
        if saw_error and saw_success:
            break
    assert saw_error, "Path NO_WASTE_DETECTED tidak pernah terpicu dalam 60 percobaan"
    assert saw_success, "Path sukses tidak pernah terpicu dalam 60 percobaan"


def test_ws_predict_binary_frame_returns_contract_fields():
    image_bytes = _make_jpeg_bytes(color=(34, 139, 34))
    with client.websocket_connect("/ws/predict") as websocket:
        websocket.send_bytes(image_bytes)
        response = websocket.receive_json()

        if "error" in response:
            assert response["error"]["code"] in {"NO_WASTE_DETECTED"}
        else:
            required_fields = {
                "requestId",
                "detectedType",
                "confidenceScore",
                "estimatedVolumeLiter",
                "organik_percent",
                "non_organik_percent",
                "detections",
                "annotatedImageBase64",
                "serverLatencyMs",
            }
            assert required_fields.issubset(response.keys())
            assert response["serverLatencyMs"] >= 0.0

        websocket.send_text("__close__")


def test_ws_predict_empty_frame_returns_error_without_closing():
    image_bytes = _make_jpeg_bytes(color=(34, 139, 34))
    with client.websocket_connect("/ws/predict") as websocket:
        websocket.send_bytes(b"")
        response = websocket.receive_json()
        assert response["error"]["code"] == "EMPTY_FRAME"

        # Koneksi harus tetap hidup -> kirim frame valid berikutnya harus jalan.
        websocket.send_bytes(image_bytes)
        response2 = websocket.receive_json()
        assert "error" in response2 or "detectedType" in response2

        websocket.send_text("__close__")


def test_ws_predict_multiple_frames_sequential():
    image_bytes = _make_jpeg_bytes(color=(200, 50, 50))  # merah -> condong NON_ORGANIC
    with client.websocket_connect("/ws/predict") as websocket:
        for _ in range(3):
            websocket.send_bytes(image_bytes)
            response = websocket.receive_json()
            assert "requestId" in response or "error" in response
        websocket.send_text("__close__")
