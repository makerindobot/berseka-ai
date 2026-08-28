"""
BERSEKA AI — Helper anotasi gambar (Backlog 6).

Menggambar bounding box hasil deteksi (mock atau model asli nanti) di atas
gambar asli, lalu encode ke base64 untuk field `annotatedImageBase64` sesuai
kontrak. Fungsi ini independen dari classifier (mock/YOLOv8) — hanya
menerima list Detection generik, jadi tetap valid dipakai setelah model
asli (Backlog 5) di-swap in.
"""

from __future__ import annotations

import base64
import io
from typing import List

from PIL import Image, ImageDraw

from api.schemas.predict_schema import Detection, DetectedType

_BOX_COLOR = {
    DetectedType.ORGANIC: (46, 204, 113),      # hijau
    DetectedType.NON_ORGANIC: (231, 76, 60),   # merah
    DetectedType.MIXED: (241, 196, 15),        # kuning
}


def draw_annotations_base64(image_bytes: bytes, detections: List[Detection]) -> str:
    """Gambar bbox di atas gambar asli, kembalikan data URI base64 (JPEG).

    Jika gambar tidak bisa dibuka/di-decode, kembalikan base64 dari
    placeholder 1x1 px transparan agar response tetap valid secara skema
    (field annotatedImageBase64 wajib ada / non-null di kontrak).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for det in detections:
            bbox = det.bbox
            x_center = bbox.x_center * w
            y_center = bbox.y_center * h
            box_w = bbox.width * w
            box_h = bbox.height * h
            x0 = max(0, x_center - box_w / 2)
            y0 = max(0, y_center - box_h / 2)
            x1 = min(w, x_center + box_w / 2)
            y1 = min(h, y_center + box_h / 2)
            color = _BOX_COLOR.get(det.label, (52, 152, 219))
            draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
            label_text = f"{det.label.value} {det.confidence:.2f}"
            draw.text((x0 + 2, max(0, y0 - 12)), label_text, fill=color)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        # Placeholder 1x1 px JPEG transparan (fallback aman, tidak pernah None)
        placeholder = Image.new("RGB", (1, 1), color=(0, 0, 0))
        buf = io.BytesIO()
        placeholder.save(buf, format="JPEG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
