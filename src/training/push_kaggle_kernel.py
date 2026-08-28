"""BERSEKA AI — Generate & push Kaggle Notebook (kernel) via Kaggle API.

Dijalankan dari GATEWAY LOKAL. Script ini:
  1. Merender file notebook (.ipynb) dari template Python (bukan draft manual) —
     sel-sel notebook di-generate terprogram dari fungsi build_notebook_cells(),
     sehingga notebook selalu sinkron dengan source code src/ (single source of truth).
  2. Menulis kernel-metadata.json (dataset_sources, GPU accelerator, enable_internet, dll).
  3. Push kernel ke Kaggle via `kaggle kernels push` (KaggleApi.kernels_push).

PENTING (kuota Kaggle):
  - Fungsi ini TIDAK menjalankan kernel secara otomatis kecuali --run diberikan.
  - Default mode `dry_run` di notebook (lihat NOTEBOOK_MODE env var yang di-inject) —
    supaya begitu kernel dijalankan pertama kali di Kaggle, ia memvalidasi pipeline
    dgn subset kecil dulu, bukan langsung full training berjam-jam.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.strip("\n").splitlines(keepends=True)}


def _md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip("\n").splitlines(keepends=True)}


def build_notebook_cells(mode: str = "dry_run") -> list[dict]:
    """Bangun sel-sel notebook secara terprogram. `mode` dikontrol lewat env var
    NOTEBOOK_MODE di dalam kernel sehingga bisa diganti ke 'full_run' tanpa
    regenerasi notebook (edit env var di Kaggle kernel settings)."""
    cells = []

    cells.append(_md_cell(f"""
# BERSEKA AI — YOLOv8 Training Pipeline (Kaggle GPU)
Auto-generated oleh `src/training/push_kaggle_kernel.py` — JANGAN edit manual di sini,
edit source di repo `berseka-ai/src/` lalu regenerasi & push ulang.

Mode saat generate: **{mode}**. Ganti env var `NOTEBOOK_MODE` di Kaggle kernel settings
(`dry_run` / `full_run`) tanpa perlu push ulang notebook untuk switch mode.

Target metrik (Backlog 1): mAP@0.5 >= 0.85, akurasi >= 90%, F1 >= 0.85, gap val-train loss <= 15%.
"""))

    cells.append(_code_cell("""
# Cek GPU yang tersedia (Kaggle biasanya kasih pilihan T4 x2 atau P100)
import subprocess
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
"""))

    cells.append(_code_cell("""
# Install dependencies (kernel Kaggle biasanya sudah punya ultralytics, dipin ulang agar konsisten)
!pip install -q ultralytics==8.2.103 albumentations opencv-python-headless pyyaml scikit-learn
"""))

    cells.append(_code_cell("""
import os, sys, shutil
from pathlib import Path

NOTEBOOK_MODE = os.environ.get("NOTEBOOK_MODE", "dry_run")  # dry_run | full_run
print("NOTEBOOK_MODE =", NOTEBOOK_MODE)

# Repo source code di-attach sebagai Kaggle Dataset (berseka-src) agar tidak perlu
# clone git di setiap run (hemat kuota API/waktu). Lihat kernel-metadata.json dataset_sources.
REPO_SRC = Path("/kaggle/input/berseka-src")
if REPO_SRC.exists():
    sys.path.insert(0, str(REPO_SRC))
    print("Source code ditemukan di", REPO_SRC)
else:
    print("[warn] dataset berseka-src belum di-attach, sebagian import bisa gagal.")
"""))

    cells.append(_code_cell("""
# --- 1) Download & gabungkan dataset ---
from src.preprocessing.dataset_acquisition import download_all

DATA_ROOT = Path("/kaggle/working/data")
only = None
if NOTEBOOK_MODE == "dry_run":
    # dry-run: cukup dataset kecil dulu untuk validasi pipeline (hemat waktu/kuota)
    only = ["waste_segregation_aashidutt3", "taco_yolo"]

downloaded = download_all(DATA_ROOT, only=only)
print(downloaded)
"""))

    cells.append(_code_cell("""
# --- 2) Terapkan label mapping (configs/label_mapping.yaml) ke TACO ---
from src.preprocessing.remap_taco_labels import remap_taco_dataset

taco_src = DATA_ROOT / "raw" / "taco_yolo"
taco_remapped = DATA_ROOT / "processed" / "taco_binary"
if taco_src.exists():
    summary = remap_taco_dataset(taco_src, taco_remapped)
    print(summary)
else:
    print("[skip] TACO YOLO belum didownload di mode ini")
"""))

    cells.append(_code_cell("""
# --- 3) Preprocessing: split train/val/test group-aware + stratified + anti-leakage ---
from src.preprocessing.split_dataset import (
    SampleRecord, default_group_id, group_aware_stratified_split, write_split_manifest, dedup_by_phash
)
import yaml

records = []
# Kumpulkan sample dari TACO ter-remap (punya bbox -> dataset_source='taco')
taco_labels_dir = taco_remapped / "train" / "labels"
if taco_remapped.exists() and taco_labels_dir.exists():
    for lbl_path in taco_labels_dir.glob("*.txt"):
        lines = lbl_path.read_text().strip().splitlines()
        if not lines:
            continue
        cls_id = int(lines[0].split()[0])
        label = "ORGANIC" if cls_id == 0 else "NON_ORGANIC"
        img_path = str(lbl_path).replace("labels", "images").replace(".txt", ".jpg")
        records.append(SampleRecord(path=img_path, label=label, dataset_source="taco",
                                     group_id=default_group_id(img_path)))

print(f"Total sample terkumpul (mode={NOTEBOOK_MODE}): {len(records)}")

if records:
    # dedup pHash HANYA dijalankan di full_run (expensive utk banyak gambar; dry-run skip)
    if NOTEBOOK_MODE == "full_run":
        records, dropped = dedup_by_phash(records, threshold=5)
        print(f"Dedup pHash: {len(dropped)} near-duplicate dibuang")

    splits = group_aware_stratified_split(records, seed=42)
    write_split_manifest(splits, DATA_ROOT / "splits", seed=42)
else:
    print("[skip] tidak ada sample untuk displit pada mode ini")
"""))

    cells.append(_code_cell("""
# --- 4) Augmentasi field-condition (motion blur, brightness jitter, dll) ---
from src.preprocessing.augmentation import build_field_condition_transform

transform = build_field_condition_transform()
print(f"Pipeline augmentasi siap: {len(transform.transforms)} operasi "
      "(motion blur, gaussian blur/noise, jpeg artifact, brightness/contrast, occlusion, hue shift)")
# Augmentasi mosaic/mixup/hsv bawaan YOLOv8 diterapkan otomatis saat model.train() (lihat sel training)
"""))

    cells.append(_code_cell("""
# --- 5) Training YOLOv8 ---
from src.training.train import train as run_training

data_yaml = str(taco_remapped / "data.yaml") if taco_remapped.exists() else None
if data_yaml:
    result = run_training(mode=NOTEBOOK_MODE, data_yaml=data_yaml, resume=True)
    print(result)
else:
    print("[skip] data.yaml belum ada, lewati training (mode verifikasi struktur saja)")
"""))

    cells.append(_code_cell("""
# --- Simpan checkpoint ke /kaggle/working agar bisa di-attach sbg Kaggle Dataset
# 'berseka-checkpoints' untuk RESUME di run berikutnya (hemat kuota GPU, tidak dari nol).
import glob, shutil
ckpt_dir = Path("/kaggle/working/checkpoints")
best_ckpts = glob.glob(str(ckpt_dir / "**" / "weights" / "last.pt"), recursive=True)
print("Checkpoint ditemukan:", best_ckpts)
# Setelah run ini selesai: buat/update Kaggle Dataset 'berseka-checkpoints' dari
# /kaggle/working/checkpoints via `kaggle datasets version` (dilakukan manual/CI terpisah
# supaya checkpoint tidak hilang saat kernel session berakhir).
"""))

    cells.append(_code_cell("""
# --- 6) Evaluasi metrik otomatis (mAP, precision, recall, F1, confusion matrix, loss curve) ---
from src.training.evaluate import evaluate

if best_ckpts:
    weights = best_ckpts[0].replace("last.pt", "best.pt")
    results_csv = str(Path(best_ckpts[0]).parent.parent / "results.csv")
    report = evaluate(weights=weights, data_yaml=data_yaml, results_csv=results_csv,
                       out_dir="/kaggle/working/eval_output")
else:
    print("[skip] tidak ada checkpoint untuk dievaluasi pada mode ini")
"""))

    return cells


def build_notebook(mode: str = "dry_run") -> dict:
    return {
        "cells": build_notebook_cells(mode),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build_kernel_metadata(username: str, kernel_slug: str, title: str) -> dict:
    """kernel-metadata.json sesuai schema kaggle CLI. `dataset_sources` mencakup
    seluruh dataset kandidat (Backlog 1) + dataset 'berseka-src' (source code repo,
    HARUS dibuat/di-upload terpisah sbg Kaggle Dataset agar kernel bisa import src/
    tanpa clone git tiap run) dan 'berseka-checkpoints' (untuk resume training).
    """
    return {
        "id": f"{username}/{kernel_slug}",
        "title": title,
        "code_file": "berseka_training_pipeline.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [
            "vencerlanz09/taco-dataset-yolo-format",
            "kneroma/tacotrashdataset",
            "sumn2u/garbage-classification-v2",
            "alistairking/recyclable-and-household-waste-classification",
            "joebeachcapital/realwaste",
            "aashidutt3/waste-segregation-image-dataset",
            f"{username}/berseka-src",
            f"{username}/berseka-checkpoints",
        ],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


def write_notebook_bundle(out_dir: str | Path, username: str, kernel_slug: str, title: str, mode: str) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nb_path = out_dir / "berseka_training_pipeline.ipynb"
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(build_notebook(mode), f, indent=1)

    meta_path = out_dir / "kernel-metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(build_kernel_metadata(username, kernel_slug, title), f, indent=2)

    print(f"[ok] notebook bundle ditulis ke {out_dir}")
    return out_dir


def push_kernel(bundle_dir: str | Path) -> None:
    """Push notebook ke Kaggle sbg kernel. Butuh KAGGLE_API_TOKEN sudah diset."""
    import os

    if not os.environ.get("KAGGLE_API_TOKEN"):
        token_path = Path.home() / ".kaggle" / "access_token"
        if token_path.exists():
            os.environ["KAGGLE_API_TOKEN"] = token_path.read_text().strip()
        else:
            raise RuntimeError("KAGGLE_API_TOKEN tidak tersedia, setup token dulu sebelum push.")

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    result = api.kernels_push(str(bundle_dir))
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate & push notebook Kaggle BERSEKA AI")
    parser.add_argument("--username", required=True, help="Username Kaggle pemilik kernel")
    parser.add_argument("--kernel-slug", default="berseka-yolov8-training", help="Slug kernel Kaggle")
    parser.add_argument("--title", default="BERSEKA AI - YOLOv8 Training Pipeline")
    parser.add_argument("--mode", choices=["dry_run", "full_run"], default="dry_run")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "notebooks" / "kaggle_kernel"))
    parser.add_argument("--push", action="store_true", help="Push ke Kaggle setelah generate (default: hanya generate lokal)")
    args = parser.parse_args()

    bundle = write_notebook_bundle(args.out_dir, args.username, args.kernel_slug, args.title, args.mode)
    if args.push:
        push_kernel(bundle)
    else:
        print("[info] notebook & metadata sudah digenerate. Jalankan ulang dengan --push untuk push ke Kaggle.")
