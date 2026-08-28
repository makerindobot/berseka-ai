"""Unit test untuk modul pre-validasi kualitas foto (Backlog 4).

Generate gambar sintetik dengan PIL/numpy (tanpa dataset asli) untuk menguji
3 skenario: blur ekstrem, gambar tajam (noise+edge), pencahayaan buruk
(gelap/overexposed), dan resolusi rendah — memverifikasi modul menolak/menerima
sesuai ekspektasi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.preprocessing.image_quality_check import (
    BLUR_VARIANCE_THRESHOLD,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    MIN_SHORT_SIDE_PX,
    check_image_quality,
)


def _sharp_image(size: int = 480, seed: int = 0) -> np.ndarray:
    """Gambar sintetik 'tajam': noise acak + checkerboard (edge kuat, high freq)."""
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 256, (size, size, 3)).astype(np.uint8)
    checker = np.indices((size, size)).sum(axis=0) % 40 < 20
    img[checker] = 255
    img[~checker] = 0
    return img


def _blurred_image(size: int = 480, seed: int = 0, ksize: int = 31) -> np.ndarray:
    """Gambar sintetik buram ekstrem: hasil blur berat dari gambar tajam."""
    sharp = _sharp_image(size=size, seed=seed)
    return cv2.GaussianBlur(sharp, (ksize, ksize), ksize / 2)


def _solid_color_image(size: int = 480, color: tuple[int, int, int] = (128, 128, 128)) -> np.ndarray:
    """Warna solid = kasus blur paling ekstrem (variansi Laplacian = 0)."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, :] = color
    return img


def _dark_image(size: int = 480, seed: int = 0) -> np.ndarray:
    """Gambar sangat gelap dengan sedikit tekstur (bukan solid, agar bukan gagal blur)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 15, (size, size, 3)).astype(np.uint8)


def _overexposed_image(size: int = 480, seed: int = 0) -> np.ndarray:
    """Gambar sangat terang/overexposed dengan sedikit tekstur."""
    rng = np.random.default_rng(seed)
    return rng.integers(240, 256, (size, size, 3)).astype(np.uint8)


def _well_lit_sharp_image(size: int = 480, seed: int = 0) -> np.ndarray:
    """Gambar 'normal': brightness moderat + tekstur cukup tajam, mensimulasikan
    foto valid tampak-atas tong sampah (dgn bentuk & warna acak, brightness dijaga
    di tengah rentang aman)."""
    rng = np.random.default_rng(seed)
    base = rng.normal(130, 45, (size, size, 3)).clip(0, 255).astype(np.uint8)
    checker = np.indices((size, size)).sum(axis=0) % 30 < 15
    base[checker] = np.clip(base[checker].astype(int) + 60, 0, 255).astype(np.uint8)
    return base


# ---- Test: blur ekstrem harus ditolak ----


def test_solid_color_rejected_as_blur():
    result = check_image_quality(_solid_color_image())
    assert result["valid"] is False
    assert "buram" in result["reason"].lower()
    assert result["metrics"]["blur_score"] < BLUR_VARIANCE_THRESHOLD


def test_heavily_blurred_image_rejected():
    result = check_image_quality(_blurred_image())
    assert result["valid"] is False
    assert "buram" in result["reason"].lower()


def test_sharp_image_passes_blur_check():
    result = check_image_quality(_sharp_image())
    # Gambar tajam (noise tinggi + checkerboard) tidak boleh ditolak karena blur.
    assert result["metrics"]["blur_score"] >= BLUR_VARIANCE_THRESHOLD
    if not result["valid"]:
        assert "buram" not in (result["reason"] or "").lower()


# ---- Test: pencahayaan buruk harus ditolak ----


def test_dark_image_rejected():
    result = check_image_quality(_dark_image())
    assert result["valid"] is False
    assert "gelap" in result["reason"].lower()
    assert result["metrics"]["brightness_score"] < BRIGHTNESS_MIN


def test_overexposed_image_rejected():
    result = check_image_quality(_overexposed_image())
    assert result["valid"] is False
    assert "terang" in result["reason"].lower()
    assert result["metrics"]["brightness_score"] > BRIGHTNESS_MAX


# ---- Test: resolusi rendah harus ditolak ----


def test_low_resolution_image_rejected():
    tiny = _well_lit_sharp_image(size=100)
    result = check_image_quality(tiny)
    assert result["valid"] is False
    assert "resolusi" in result["reason"].lower()
    assert result["metrics"]["resolution"]["width"] < MIN_SHORT_SIDE_PX


# ---- Test: gambar yang memenuhi semua kriteria harus diterima ----


def test_well_lit_sharp_image_accepted():
    result = check_image_quality(_well_lit_sharp_image())
    assert result["valid"] is True
    assert result["reason"] is None
    assert result["metrics"]["blur_score"] >= BLUR_VARIANCE_THRESHOLD
    assert BRIGHTNESS_MIN <= result["metrics"]["brightness_score"] <= BRIGHTNESS_MAX


# ---- Test: struktur return value ----


def test_return_schema_has_required_keys():
    result = check_image_quality(_well_lit_sharp_image())
    assert set(result.keys()) == {"valid", "reason", "metrics"}
    metrics = result["metrics"]
    assert set(metrics.keys()) == {
        "blur_score",
        "brightness_score",
        "clipped_pixel_ratio",
        "resolution",
    }
    assert set(metrics["resolution"].keys()) == {"width", "height"}


def test_invalid_none_image_rejected_gracefully():
    result = check_image_quality(np.zeros((0, 0, 3), dtype=np.uint8))
    assert result["valid"] is False
    assert result["reason"] is not None


if __name__ == "__main__":
    test_solid_color_rejected_as_blur()
    test_heavily_blurred_image_rejected()
    test_sharp_image_passes_blur_check()
    test_dark_image_rejected()
    test_overexposed_image_rejected()
    test_low_resolution_image_rejected()
    test_well_lit_sharp_image_accepted()
    test_return_schema_has_required_keys()
    test_invalid_none_image_rejected_gracefully()
    print("[ok] semua unit test image_quality_check lulus")
