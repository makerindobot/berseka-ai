"""BERSEKA AI — Pre-validasi kualitas foto sebelum inference (Backlog 4).

Warga awam memfoto pakai HP mereka sendiri — hasil bisa buram (tangan gemetar/
autofocus gagal), pencahayaan buruk (indoor gelap / backlight / overexposed
flash), atau resolusi terlalu kecil (thumbnail/kompresi berat aplikasi chat).
Modul ini adalah GATE yang dipanggil SEBELUM foto masuk ke model YOLOv8
(integrasi endpoint /predict adalah scope Backlog 6, BUKAN modul ini) — tujuannya
mencegah model menghasilkan estimasi ngawur dari input yang secara fundamental
tidak bisa dianalisis akurat.

Tiga pemeriksaan, urutan dari termurah/paling fundamental ke termahal:
  1. Resolusi — foto terlalu kecil untuk dianalisis akurat.
  2. Pencahayaan — histogram brightness grayscale (terlalu gelap/terlalu terang).
  3. Blur/ketajaman — variansi Laplacian (cv2.Laplacian(img, cv2.CV_64F).var()).

Threshold & rasionalnya didokumentasikan di
`docs/architecture/image-quality-gate.md` (WAJIB dibaca sebelum mengubah
angka di bawah — jangan hardcode ulang di tempat lain, ubah di satu tempat ini
sesuai konvensi single-source-of-truth proyek, mirip `configs/label_mapping.yaml`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# --- Threshold konfigurasi (lihat docs/architecture/image-quality-gate.md) ---

# Blur: variansi Laplacian di bawah ini dianggap terlalu buram untuk dianalisis.
# Diverifikasi empiris (lihat dokumen arsitektur): foto tajam sintetik ~290-330,
# blur ringan (gaussian k=3) sudah jatuh ke ~20-50, blur berat mendekati 0.
# 100 memberi margin aman di antara "tajam" dan "blur ringan sekalipun".
BLUR_VARIANCE_THRESHOLD = 100.0

# Pencahayaan: rata-rata brightness grayscale (skala 0-255).
# Di bawah MIN dianggap terlalu gelap, di atas MAX dianggap overexposed.
BRIGHTNESS_MIN = 40.0
BRIGHTNESS_MAX = 215.0

# Pencahayaan: proporsi maksimum piksel yang "clipped" (nyaris hitam murni atau
# nyaris putih murni) sebelum foto dianggap kehilangan detail signifikan,
# walau rata-rata brightness masih dalam rentang wajar (mis. foto dgn area gelap
# pekat + area sangat terang berdampingan / backlight parah).
CLIPPED_PIXEL_RATIO_MAX = 0.55

# Resolusi: dimensi minimum (piksel) di sisi terpendek agar YOLOv8 punya cukup
# detail untuk deteksi objek & estimasi area/volume yang akurat.
MIN_SHORT_SIDE_PX = 320
MIN_TOTAL_PIXELS = 320 * 320


@dataclass
class QualityMetrics:
    blur_score: float
    brightness_score: float
    clipped_pixel_ratio: float
    resolution: tuple[int, int]  # (width, height)

    def to_dict(self) -> dict[str, Any]:
        return {
            "blur_score": round(self.blur_score, 2),
            "brightness_score": round(self.brightness_score, 2),
            "clipped_pixel_ratio": round(self.clipped_pixel_ratio, 4),
            "resolution": {"width": self.resolution[0], "height": self.resolution[1]},
        }


@dataclass
class QualityCheckResult:
    valid: bool
    reason: str | None
    metrics: QualityMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "metrics": self.metrics.to_dict(),
        }


def _compute_blur_score(gray: np.ndarray) -> float:
    """Variansi Laplacian — proxy ketajaman/sharpness standar OpenCV community.
    Nilai rendah = tepi/edge lemah = kemungkinan besar buram."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _compute_brightness_metrics(gray: np.ndarray) -> tuple[float, float]:
    """Return (mean_brightness, clipped_pixel_ratio) dari histogram grayscale."""
    mean_brightness = float(gray.mean())
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    total_px = gray.size
    # "Clipped" = sangat gelap (<=10) atau sangat terang (>=245) — kehilangan detail.
    clipped = hist[:11].sum() + hist[245:].sum()
    clipped_ratio = float(clipped / total_px) if total_px else 0.0
    return mean_brightness, clipped_ratio


def check_image_quality(
    image: np.ndarray | str | Path,
    *,
    blur_threshold: float = BLUR_VARIANCE_THRESHOLD,
    brightness_min: float = BRIGHTNESS_MIN,
    brightness_max: float = BRIGHTNESS_MAX,
    clipped_ratio_max: float = CLIPPED_PIXEL_RATIO_MAX,
    min_short_side_px: int = MIN_SHORT_SIDE_PX,
    min_total_pixels: int = MIN_TOTAL_PIXELS,
) -> dict[str, Any]:
    """Validasi kualitas 1 foto sebelum dikirim ke model inference.

    Args:
        image: array BGR (hasil cv2.imread / frame kamera) ATAU path ke file gambar.
        blur_threshold / brightness_* / clipped_ratio_max / min_*: override threshold
            untuk keperluan testing; nilai default mengikuti konfigurasi resmi di atas.

    Returns:
        dict dengan skema:
        {
            "valid": bool,
            "reason": str | None,   # None jika valid, pesan jelas jika tidak
            "metrics": {
                "blur_score": float,
                "brightness_score": float,
                "clipped_pixel_ratio": float,
                "resolution": {"width": int, "height": int},
            }
        }

    Urutan pengecekan (fail-fast, cek termurah/paling fundamental dulu):
        1. Gambar valid & bisa dibaca
        2. Resolusi cukup besar
        3. Pencahayaan wajar (tidak terlalu gelap/terang, tidak banyak clipping)
        4. Ketajaman cukup (bukan blur)
    """
    img = _load_as_bgr_array(image)

    if img is None or img.size == 0:
        return QualityCheckResult(
            valid=False,
            reason="Gambar tidak valid atau tidak bisa dibaca.",
            metrics=QualityMetrics(
                blur_score=0.0, brightness_score=0.0, clipped_pixel_ratio=0.0, resolution=(0, 0)
            ),
        ).to_dict()

    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img

    blur_score = _compute_blur_score(gray)
    brightness_score, clipped_ratio = _compute_brightness_metrics(gray)

    metrics = QualityMetrics(
        blur_score=blur_score,
        brightness_score=brightness_score,
        clipped_pixel_ratio=clipped_ratio,
        resolution=(width, height),
    )

    # 1. Resolusi
    short_side = min(width, height)
    total_pixels = width * height
    if short_side < min_short_side_px or total_pixels < min_total_pixels:
        return QualityCheckResult(
            valid=False,
            reason=(
                f"Resolusi terlalu rendah ({width}x{height}px). "
                f"Minimum sisi terpendek {min_short_side_px}px agar objek sampah "
                "bisa dideteksi akurat. Coba foto ulang tanpa memperkecil/kompresi berat."
            ),
            metrics=metrics,
        ).to_dict()

    # 2. Pencahayaan — terlalu gelap
    if brightness_score < brightness_min:
        return QualityCheckResult(
            valid=False,
            reason=(
                f"Foto terlalu gelap (brightness rata-rata {brightness_score:.1f}/255, "
                f"minimum {brightness_min:.0f}). Ambil foto di tempat lebih terang atau "
                "nyalakan lampu/flash."
            ),
            metrics=metrics,
        ).to_dict()

    # 2b. Pencahayaan — terlalu terang (overexposed)
    if brightness_score > brightness_max:
        return QualityCheckResult(
            valid=False,
            reason=(
                f"Foto terlalu terang/overexposed (brightness rata-rata "
                f"{brightness_score:.1f}/255, maksimum {brightness_max:.0f}). "
                "Hindari cahaya langsung/flash terlalu dekat, coba ulang."
            ),
            metrics=metrics,
        ).to_dict()

    # 2c. Pencahayaan — terlalu banyak area clipped (kontras ekstrem/backlight)
    if clipped_ratio > clipped_ratio_max:
        return QualityCheckResult(
            valid=False,
            reason=(
                f"Pencahayaan terlalu kontras ({clipped_ratio * 100:.0f}% piksel "
                "gelap/terang pekat kehilangan detail). Hindari backlight (sumber "
                "cahaya di belakang objek), coba ulang."
            ),
            metrics=metrics,
        ).to_dict()

    # 3. Blur
    if blur_score < blur_threshold:
        return QualityCheckResult(
            valid=False,
            reason=(
                f"Foto buram (skor ketajaman {blur_score:.1f}, minimum "
                f"{blur_threshold:.0f}). Pastikan kamera fokus & tangan stabil "
                "saat memfoto, lalu coba ulang."
            ),
            metrics=metrics,
        ).to_dict()

    return QualityCheckResult(valid=True, reason=None, metrics=metrics).to_dict()


def _load_as_bgr_array(image: np.ndarray | str | Path) -> np.ndarray | None:
    if isinstance(image, (str, Path)):
        return cv2.imread(str(image), cv2.IMREAD_COLOR)
    if isinstance(image, np.ndarray):
        return image
    raise TypeError(f"Tipe image tidak didukung: {type(image)}")


if __name__ == "__main__":
    # smoke test kecil: pastikan modul bisa jalan pada gambar sintetik
    solid = np.full((480, 480, 3), 128, dtype=np.uint8)
    result = check_image_quality(solid)
    print(f"[ok] solid color -> valid={result['valid']} reason={result['reason']}")
    assert result["valid"] is False
