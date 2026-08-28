"""
BERSEKA AI — FastAPI Model Serving API entrypoint (Backlog 6).

Menjalankan:
  - POST /predict          -> api/routes/predict.py
  - WS   /ws/predict        -> api/routes/ws_predict.py

// TODO: replace dengan model YOLOv8 hasil training Backlog 5 (lihat
komentar TODO di api/services/mock_classifier.py) — struktur API di file
ini TIDAK perlu berubah saat model asli di-swap in, karena
routes/predict.py & routes/ws_predict.py hanya bergantung pada interface
`predict_async()` yang dipertahankan sama.

Jalankan lokal:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
(dijalankan dari root repo `berseka-ai/`, bukan dari dalam folder `api/`,
supaya import `api.routes...` / `api.services...` resolve dengan benar.)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.predict import router as predict_router
from api.routes.ws_predict import router as ws_predict_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="BERSEKA AI — Model Serving API",
    description=(
        "Model serving API untuk BERSEKA AI (Waste Sorting Compliance Monitoring, "
        "Kec. Coblong x UNIKOM). Backlog 6. SAAT INI memakai mock/stub classifier "
        "karena model YOLOv8 asli (Backlog 5) masih menunggu dataset lapangan & "
        "training run GPU."
    ),
    version="0.1.0-mock",
)

# CORS longgar untuk kebutuhan integrasi dashboard (Backlog 8) & backend
# Node.js adapter (Backlog 7) saat development. Perketat origin saat deploy
# produksi (Backlog 11).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router, tags=["predict"])
app.include_router(ws_predict_router, tags=["ws-predict"])


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict:
    """Health check sederhana untuk load balancer / monitoring (Backlog 11)."""
    return {"status": "ok", "model": "mock_classifier", "note": "YOLOv8 asli belum di-plug-in (Backlog 5)"}


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Alias /health (beberapa monitoring tool default cek path ini)."""
    return await healthz()
