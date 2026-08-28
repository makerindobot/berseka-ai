"""BERSEKA AI — Evaluasi metrik model YOLOv8, otomatis jalan setelah training.

Menghasilkan:
  - mAP@0.5, mAP@0.5:0.95, precision, recall, F1 (dari ultralytics model.val())
  - Confusion matrix (disimpan sbg PNG + raw counts JSON)
  - Grafik train-vs-val loss curve (dari results.csv ultralytics)
  - Gate lolos/tidak terhadap target_metrics di configs/training_config.yaml
    (mAP@0.5 >= 0.85, akurasi >= 0.90, F1 >= 0.85, gap val-train loss <= 15%)

Dipanggil otomatis di akhir src/training/train.py (mode full_run) ATAU manual:
    python -m src.training.evaluate --weights runs/best.pt --data-yaml data.yaml --results-csv runs/results.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.utils.config_loader import load_training_config


def compute_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def run_ultralytics_val(weights: str, data_yaml: str, imgsz: int = 640) -> dict:
    from ultralytics import YOLO

    model = YOLO(weights)
    metrics = model.val(data=data_yaml, imgsz=imgsz, plots=True)

    # ultralytics DetMetrics: box.map (mAP50-95), box.map50, box.mp (precision), box.mr (recall)
    precision = float(metrics.box.mp)
    recall = float(metrics.box.mr)
    map50 = float(metrics.box.map50)
    map5095 = float(metrics.box.map)
    f1 = compute_f1(precision, recall)

    confusion_matrix = None
    try:
        cm = metrics.confusion_matrix.matrix  # numpy array (nc+1) x (nc+1) incl. background
        confusion_matrix = cm.tolist()
    except Exception as e:  # noqa: BLE001
        print(f"[warn] gagal ekstrak confusion matrix: {e}")

    return {
        "precision": precision,
        "recall": recall,
        "map50": map50,
        "map50_95": map5095,
        "f1": f1,
        "confusion_matrix": confusion_matrix,
        "class_names": ["ORGANIC", "NON_ORGANIC"],
        "save_dir": str(metrics.save_dir) if hasattr(metrics, "save_dir") else None,
    }


def compute_accuracy_from_confusion(confusion_matrix: list[list[float]] | None) -> float | None:
    """Akurasi klasifikasi dari confusion matrix deteksi (diag / total), sbg proksi
    'akurasi' selain mAP — sesuai target metrik Backlog 1 (akurasi >= 90%)."""
    if not confusion_matrix:
        return None
    import numpy as np

    cm = np.array(confusion_matrix)
    correct = float(np.trace(cm))
    total = float(cm.sum())
    if total == 0:
        return None
    return correct / total


def plot_loss_curve(results_csv: str, out_path: str) -> dict | None:
    """Baca results.csv ultralytics (per-epoch train/val loss), plot & hitung gap%."""
    try:
        import pandas as pd
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[warn] pandas/matplotlib tidak tersedia, skip loss curve")
        return None

    csv_path = Path(results_csv)
    if not csv_path.exists():
        print(f"[warn] results.csv tidak ditemukan di {csv_path}, skip loss curve")
        return None

    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    train_col = next((c for c in df.columns if "train/box_loss" in c), None)
    val_col = next((c for c in df.columns if "val/box_loss" in c), None)
    if not train_col or not val_col:
        print(f"[warn] kolom loss tidak ditemukan di {list(df.columns)}")
        return None

    plt.figure(figsize=(8, 5))
    plt.plot(df["epoch"], df[train_col], label="train box_loss")
    plt.plot(df["epoch"], df[val_col], label="val box_loss")
    plt.xlabel("epoch")
    plt.ylabel("box_loss")
    plt.title("BERSEKA AI — Train vs Val Loss (YOLOv8)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

    final_train = float(df[train_col].iloc[-1])
    final_val = float(df[val_col].iloc[-1])
    gap_pct = abs(final_val - final_train) / max(final_train, 1e-9) * 100
    return {"final_train_loss": final_train, "final_val_loss": final_val, "gap_pct": gap_pct, "plot_path": out_path}


def check_gate(metrics: dict, loss_info: dict | None, config_path: str | None = None) -> dict:
    """Bandingkan metrik hasil terhadap target_metrics Backlog 1, hasilkan verdict."""
    cfg = load_training_config(config_path)["target_metrics"]
    accuracy = compute_accuracy_from_confusion(metrics.get("confusion_matrix"))

    checks = {
        "map50": {
            "value": metrics["map50"],
            "target": cfg["map50_min"],
            "pass": metrics["map50"] >= cfg["map50_min"],
        },
        "f1": {
            "value": metrics["f1"],
            "target": cfg["f1_min"],
            "pass": metrics["f1"] >= cfg["f1_min"],
        },
        "accuracy": {
            "value": accuracy,
            "target": cfg["accuracy_min"],
            "pass": (accuracy is not None) and (accuracy >= cfg["accuracy_min"]),
        },
    }
    if loss_info:
        checks["train_val_loss_gap"] = {
            "value": loss_info["gap_pct"],
            "target": cfg["max_train_val_loss_gap_pct"],
            "pass": loss_info["gap_pct"] <= cfg["max_train_val_loss_gap_pct"],
        }
    else:
        checks["train_val_loss_gap"] = {"value": None, "target": cfg["max_train_val_loss_gap_pct"], "pass": None}

    overall_pass = all(c["pass"] for c in checks.values() if c["pass"] is not None) and all(
        c["pass"] is not None for c in checks.values()
    )
    return {"checks": checks, "overall_pass": overall_pass}


def evaluate(
    weights: str,
    data_yaml: str,
    results_csv: str | None = None,
    out_dir: str = "eval_output",
    config_path: str | None = None,
) -> dict:
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    metrics = run_ultralytics_val(weights, data_yaml)

    loss_info = None
    if results_csv:
        loss_info = plot_loss_curve(results_csv, str(out_dir_p / "train_val_loss_curve.png"))

    gate = check_gate(metrics, loss_info, config_path)

    report = {
        "metrics": {k: v for k, v in metrics.items() if k != "confusion_matrix"},
        "confusion_matrix": metrics.get("confusion_matrix"),
        "loss_curve": loss_info,
        "gate": gate,
    }
    report_path = out_dir_p / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=== BERSEKA AI — Ringkasan Evaluasi ===")
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(gate, indent=2))
    print(f"Lolos target Backlog 1? {'YA' if gate['overall_pass'] else 'BELUM'}")
    print(f"Laporan lengkap: {report_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BERSEKA AI - evaluasi metrik YOLOv8")
    parser.add_argument("--weights", required=True, help="Path best.pt hasil training")
    parser.add_argument("--data-yaml", required=True)
    parser.add_argument("--results-csv", default=None, help="Path results.csv ultralytics (untuk loss curve)")
    parser.add_argument("--out-dir", default="eval_output")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    evaluate(args.weights, args.data_yaml, args.results_csv, args.out_dir, args.config)
