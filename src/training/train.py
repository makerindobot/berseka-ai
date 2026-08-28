"""BERSEKA AI — Training script YOLOv8 (ultralytics), didesain untuk jalan di Kaggle
kernel (GPU T4x2 / P100) TAPI juga bisa dites lokal di CPU dgn subset kecil (dry-run).

Fitur kunci sesuai kebutuhan kuota Kaggle terbatas (30 jam GPU/minggu, limit API
tiap 5 jam — lihat docs/architecture/training-pipeline.md):
  - Mode `dry_run`: subset data kecil, epoch sedikit, untuk validasi pipeline SEBELUM
    menghabiskan kuota GPU pada full run.
  - Checkpoint & resume otomatis: training TIDAK pernah mulai dari nol jika ada
    checkpoint valid di paths.resume_checkpoint (`last.pt`). Wajib simpan checkpoint
    ke Kaggle Dataset output antar sesi (lihat notebook generator).
  - save_period diatur agar checkpoint sering (default tiap 5 epoch) sehingga sesi
    yang terputus di tengah (timeout Kaggle, kuota habis) tidak kehilangan progres.

Cara pakai (dari Kaggle kernel ATAU lokal):
    python -m src.training.train --mode dry_run --data-yaml /path/data.yaml
    python -m src.training.train --mode full_run --data-yaml /path/data.yaml --resume
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

from src.utils.config_loader import load_training_config


def set_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def find_resume_checkpoint(cfg: dict) -> Path | None:
    resume_path = Path(cfg["paths"]["resume_checkpoint"])
    if resume_path.exists():
        print(f"[resume] checkpoint ditemukan: {resume_path}")
        return resume_path
    print("[resume] tidak ada checkpoint sebelumnya, training dari base pretrained model.")
    return None


def build_train_args(cfg: dict, mode: str, data_yaml: str, resume: bool) -> dict:
    profile = cfg["training"][mode]
    model_arch = cfg["model"]["architecture"] if mode == "dry_run" else cfg["model"]["architecture_full_run"]
    aug = cfg["augmentation"]["ultralytics_builtin"]

    args = dict(
        data=data_yaml,
        epochs=profile["epochs"],
        batch=profile["batch"],
        imgsz=profile["imgsz"],
        device=profile.get("device", 0),
        workers=profile.get("workers", 2),
        seed=cfg["seed"],
        project=cfg["paths"]["checkpoint_dir"],
        name=f"berseka_yolov8_{mode}",
        exist_ok=True,
        patience=profile.get("patience", 0),
        **aug,
    )
    if mode == "full_run":
        args.update(
            save_period=profile["save_period"],
            optimizer=profile["optimizer"],
            lr0=profile["lr0"],
            cos_lr=profile["cos_lr"],
            label_smoothing=profile["label_smoothing"],
            close_mosaic=profile["close_mosaic"],
        )
    if resume:
        args["resume"] = True
    return {"model_arch": model_arch, "train_args": args}


def make_dry_run_subset(data_yaml_path: str, subset_fraction: float, out_dir: str) -> str:
    """Bangun data.yaml sementara yang menunjuk ke subset kecil train/val untuk dry-run,
    tanpa mengubah dataset asli. Return path data.yaml subset."""
    import yaml

    data_yaml_p = Path(data_yaml_path)
    with open(data_yaml_p) as f:
        spec = yaml.safe_load(f)
    root = Path(spec.get("path", data_yaml_p.parent))
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    def subset_split(split_rel: str) -> str:
        split_dir = root / split_rel
        img_dir = split_dir if split_dir.name == "images" else split_dir
        images = sorted([p for p in img_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        n = max(1, int(len(images) * subset_fraction))
        chosen = images[:n]
        dst_img_dir = out_dir_p / split_rel
        dst_lbl_dir = out_dir_p / split_rel.replace("images", "labels")
        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)
        src_lbl_dir = Path(str(img_dir).replace("images", "labels"))
        for img_path in chosen:
            shutil.copy2(img_path, dst_img_dir / img_path.name)
            lbl_path = src_lbl_dir / (img_path.stem + ".txt")
            if lbl_path.exists():
                shutil.copy2(lbl_path, dst_lbl_dir / lbl_path.name)
        return split_rel

    new_spec = {"path": str(out_dir_p), "nc": spec["nc"], "names": spec["names"]}
    for key in ("train", "val", "test"):
        if key in spec and spec[key]:
            new_spec[key] = subset_split(spec[key])

    out_yaml = out_dir_p / "data.yaml"
    with open(out_yaml, "w") as f:
        yaml.safe_dump(new_spec, f, sort_keys=False)
    print(f"[dry_run] subset {subset_fraction*100:.1f}% ditulis ke {out_yaml}")
    return str(out_yaml)


def train(mode: str, data_yaml: str, resume: bool = False, config_path: str | None = None) -> dict:
    cfg = load_training_config(config_path)
    set_seed(cfg["seed"])

    if mode == "dry_run":
        subset_frac = cfg["training"]["dry_run"]["subset_fraction"]
        data_yaml = make_dry_run_subset(data_yaml, subset_frac, out_dir="/tmp/berseka_dry_run_subset")

    resume_ckpt = find_resume_checkpoint(cfg) if resume else None
    built = build_train_args(cfg, mode, data_yaml, resume=bool(resume_ckpt))

    from ultralytics import YOLO

    model_source = str(resume_ckpt) if resume_ckpt else built["model_arch"]
    model = YOLO(model_source)

    print(f"=== BERSEKA AI — Training YOLOv8 (mode={mode}) ===")
    print(json.dumps({k: v for k, v in built["train_args"].items()}, indent=2, default=str))

    results = model.train(**built["train_args"])

    out_summary = {
        "mode": mode,
        "model_arch": built["model_arch"],
        "save_dir": str(results.save_dir) if hasattr(results, "save_dir") else None,
    }
    print("=== Training selesai ===")
    print(json.dumps(out_summary, indent=2))
    return out_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BERSEKA AI - training YOLOv8")
    parser.add_argument("--mode", choices=["dry_run", "full_run"], default="dry_run")
    parser.add_argument("--data-yaml", required=True, help="Path ke data.yaml (format YOLO, 2 kelas)")
    parser.add_argument("--resume", action="store_true", help="Resume dari checkpoint terakhir bila ada")
    parser.add_argument("--config", default=None, help="Override path configs/training_config.yaml")
    args = parser.parse_args()
    train(mode=args.mode, data_yaml=args.data_yaml, resume=args.resume, config_path=args.config)
