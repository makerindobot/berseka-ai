"""BERSEKA AI — Augmentasi offline (Albumentations) untuk simulasi kondisi lapangan HP warga.

Dipakai TERPISAH dari augmentasi bawaan ultralytics (mosaic/mixup/hsv, yg berjalan
on-the-fly saat training). Modul ini untuk:
  1. Pre-generate sample tambahan (oversampling) khusus kelas ORGANIC yang under-represented.
  2. Menyediakan fungsi transform yang bisa dipanggil manual saat butuh cek visual
     kualitas augmentasi (dry-run) sebelum dipakai skala penuh.

Parameter SEMUA diambil dari configs/training_config.yaml -> augmentation.albumentations_extra,
bukan hardcode di sini, supaya auditable & mudah tuning dari 1 tempat.
"""
from __future__ import annotations

from pathlib import Path

import albumentations as A
import cv2
import numpy as np

from src.utils.config_loader import load_training_config


def build_field_condition_transform(bbox_format: str = "yolo") -> A.Compose:
    """Bangun pipeline Albumentations dari config, mensimulasikan kondisi lapangan:
    motion blur, brightness/contrast jitter, JPEG artifact, noise, occlusion, hue shift.
    """
    cfg = load_training_config()["augmentation"]["albumentations_extra"]
    ops = []

    if cfg["motion_blur"]["enabled"]:
        ops.append(A.MotionBlur(blur_limit=cfg["motion_blur"]["blur_limit"], p=cfg["motion_blur"]["p"]))
    if cfg["gaussian_blur"]["enabled"]:
        ops.append(A.GaussianBlur(blur_limit=tuple(cfg["gaussian_blur"]["blur_limit"]), p=cfg["gaussian_blur"]["p"]))
    if cfg["gaussian_noise"]["enabled"]:
        vl = cfg["gaussian_noise"]["var_limit"]
        # albumentations>=1.4 pakai std_range (0..1) menggantikan var_limit lama;
        # konversi kasar var(0-255^2 scale) -> std fraction agar tetap sesuai konfigurasi.
        std_range = (min(1.0, (vl[0] ** 0.5) / 255), min(1.0, (vl[1] ** 0.5) / 255))
        ops.append(A.GaussNoise(std_range=std_range, p=cfg["gaussian_noise"]["p"]))
    if cfg["jpeg_compression"]["enabled"]:
        ops.append(
            A.ImageCompression(
                quality_range=(cfg["jpeg_compression"]["quality_lower"], cfg["jpeg_compression"]["quality_upper"]),
                p=cfg["jpeg_compression"]["p"],
            )
        )
    if cfg["random_brightness_contrast"]["enabled"]:
        rbc = cfg["random_brightness_contrast"]
        ops.append(
            A.RandomBrightnessContrast(
                brightness_limit=rbc["brightness_limit"],
                contrast_limit=rbc["contrast_limit"],
                p=rbc["p"],
            )
        )
    if cfg["coarse_dropout_occlusion"]["enabled"]:
        cdo = cfg["coarse_dropout_occlusion"]
        ops.append(
            A.CoarseDropout(
                num_holes_range=(1, cdo["max_holes"]),
                hole_height_range=(0.05, cdo["max_height_ratio"]),
                hole_width_range=(0.05, cdo["max_width_ratio"]),
                p=cdo["p"],
            )
        )
    if cfg["color_jitter_hue"]["enabled"]:
        cjh = cfg["color_jitter_hue"]
        ops.append(A.HueSaturationValue(hue_shift_limit=cjh["hue_shift_limit"], p=cjh["p"]))

    bbox_params = A.BboxParams(format=bbox_format, label_fields=["class_labels"], min_visibility=0.1)
    return A.Compose(ops, bbox_params=bbox_params)


def augment_image_with_bboxes(
    image: np.ndarray,
    bboxes: list[list[float]],
    class_labels: list[int],
    transform: A.Compose | None = None,
) -> tuple[np.ndarray, list[list[float]], list[int]]:
    """Terapkan augmentasi ke 1 gambar + bbox YOLO-format (cx,cy,w,h normalized)."""
    transform = transform or build_field_condition_transform()
    result = transform(image=image, bboxes=bboxes, class_labels=class_labels)
    return result["image"], result["bboxes"], result["class_labels"]


def oversample_organic_crops(
    src_dir: str | Path,
    dst_dir: str | Path,
    multiplier: int = 3,
) -> int:
    """Generate augmented copies untuk classifier-only crops (tanpa bbox) kelas ORGANIC,
    dipakai untuk mitigasi ketimpangan kelas (§4.2 dataset-decision.md). Return jumlah
    file baru yang dihasilkan.
    """
    src_dir, dst_dir = Path(src_dir), Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    transform = A.Compose(
        [t for t in build_field_condition_transform(bbox_format="yolo").transforms],
    )
    # transform di atas dibangun dengan bbox_params — untuk classifier tanpa bbox
    # kita pakai versi tanpa bbox_params agar tidak error saat tidak ada bboxes.
    classifier_transform = A.Compose(list(transform.transforms))

    count = 0
    for img_path in sorted(src_dir.glob("*.jpg")) + sorted(src_dir.glob("*.png")):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        for i in range(multiplier):
            augmented = classifier_transform(image=img)["image"]
            out_path = dst_dir / f"{img_path.stem}_aug{i}{img_path.suffix}"
            cv2.imwrite(str(out_path), augmented)
            count += 1
    return count


if __name__ == "__main__":
    # smoke test kecil: pastikan pipeline transform bisa dibangun dari config
    t = build_field_condition_transform()
    print(f"[ok] pipeline augmentasi terbentuk dengan {len(t.transforms)} operasi")
