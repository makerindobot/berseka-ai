"""BERSEKA AI — Split train/val/test anti-data-leakage.

Implementasi §5 docs/dataset/dataset-decision.md:
  1. Split di level gambar SUMBER ASLI, sebelum augmentasi.
  2. Group-aware: seluruh foto dari 1 grup/kejadian (mis. multi-angle 1 lokasi litter
     TACO) tetap 1 partisi. Group id default = filename tanpa suffix varian bila tidak
     ada metadata eksplisit; caller bisa suplai group_id_fn kustom per dataset.
  3. Stratifikasi ganda: label biner DAN dataset asal.
  4. Dedup pHash lintas dataset SEBELUM split final (opsional, expensive -> flag).
  5. Random seed tetap & dicatat di configs/split_seed.txt.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from sklearn.model_selection import GroupShuffleSplit


@dataclass
class SampleRecord:
    path: str
    label: str          # "ORGANIC" | "NON_ORGANIC"
    dataset_source: str  # key dari label_mapping.yaml dataset_sources
    group_id: str        # default = stem filename (override per dataset bila ada metadata sesi)
    phash: str | None = field(default=None)


def default_group_id(path: str) -> str:
    """Group id default: nama file tanpa ekstensi. Dataset dengan metadata sesi/lokasi
    eksplisit (mis. TACO scene_id) sebaiknya suplai group_id_fn kustom yang lebih akurat."""
    return Path(path).stem


def compute_phash(image_path: str) -> str | None:
    """pHash 8x8 sederhana via PIL saja (tanpa dependency imagehash) agar tetap ringan.
    Return None bila gambar gagal dibaca (dicatat sbg warning oleh caller)."""
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(image_path).convert("L").resize((32, 32), Image.LANCZOS)
        arr = np.asarray(img, dtype=float)
        dct = _dct2(arr)
        dct_low = dct[:8, :8]
        med = np.median(dct_low)
        bits = (dct_low > med).flatten()
        return "".join("1" if b else "0" for b in bits)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] gagal hitung phash untuk {image_path}: {e}")
        return None


def _dct2(a):
    import numpy as np
    from scipy.fftpack import dct

    return dct(dct(a.T, norm="ortho").T, norm="ortho")


def hamming(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def dedup_by_phash(records: list[SampleRecord], threshold: int = 5) -> tuple[list[SampleRecord], list[str]]:
    """Buang near-duplicate lintas dataset (mempertahankan kemunculan pertama).
    Return (records_bersih, list_path_yang_dibuang)."""
    kept: list[SampleRecord] = []
    kept_hashes: list[str] = []
    dropped: list[str] = []
    for rec in records:
        if rec.phash is None:
            kept.append(rec)
            continue
        is_dup = any(hamming(rec.phash, h) <= threshold for h in kept_hashes)
        if is_dup:
            dropped.append(rec.path)
        else:
            kept.append(rec)
            kept_hashes.append(rec.phash)
    return kept, dropped


def group_aware_stratified_split(
    records: list[SampleRecord],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, list[SampleRecord]]:
    """Split group-aware dengan stratifikasi ganda (label x dataset_source).

    Karena scikit-learn tidak punya "group-aware multi-label stratified split" siap
    pakai, strategi: bagi per stratum (label, dataset_source) dengan GroupShuffleSplit
    2 tahap (train vs temp, lalu temp -> val/test), lalu gabungkan. Ini menjaga proporsi
    tiap stratum di ketiga partisi sekaligus mencegah 1 grup tersebar ke >1 partisi.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "rasio split harus total 1.0"

    strata: dict[tuple[str, str], list[SampleRecord]] = defaultdict(list)
    for rec in records:
        strata[(rec.label, rec.dataset_source)].append(rec)

    out: dict[str, list[SampleRecord]] = {"train": [], "val": [], "test": []}

    for key, recs in strata.items():
        groups = [r.group_id for r in recs]
        n_unique_groups = len(set(groups))
        if n_unique_groups < 3:
            # terlalu sedikit grup untuk split proporsional aman -> semua ke train,
            # dicatat sbg warning (biasanya stratum kecil/edge-case dataset kecil)
            print(f"[warn] stratum {key} hanya {n_unique_groups} grup unik, semua dialokasikan ke train")
            out["train"].extend(recs)
            continue

        gss1 = GroupShuffleSplit(n_splits=1, train_size=train_ratio, random_state=seed)
        idx_all = list(range(len(recs)))
        train_idx, temp_idx = next(gss1.split(idx_all, groups=groups))

        temp_recs = [recs[i] for i in temp_idx]
        temp_groups = [groups[i] for i in temp_idx]
        val_share_of_temp = val_ratio / (val_ratio + test_ratio) if (val_ratio + test_ratio) > 0 else 0.5

        if len(set(temp_groups)) < 2:
            # tidak cukup grup buat pecah val/test -> masukkan semua temp ke val
            out["train"].extend(recs[i] for i in train_idx)
            out["val"].extend(temp_recs)
            continue

        gss2 = GroupShuffleSplit(n_splits=1, train_size=val_share_of_temp, random_state=seed)
        val_idx, test_idx = next(gss2.split(list(range(len(temp_recs))), groups=temp_groups))

        out["train"].extend(recs[i] for i in train_idx)
        out["val"].extend(temp_recs[i] for i in val_idx)
        out["test"].extend(temp_recs[i] for i in test_idx)

    return out


def write_split_manifest(splits: dict[str, list[SampleRecord]], out_dir: str | Path, seed: int) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for split_name, recs in splits.items():
        csv_path = out_dir / f"{split_name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["path", "label", "dataset_source", "group_id"])
            for r in recs:
                writer.writerow([r.path, r.label, r.dataset_source, r.group_id])

    stats = {
        split: {
            "n_samples": len(recs),
            "n_organic": sum(1 for r in recs if r.label == "ORGANIC"),
            "n_non_organic": sum(1 for r in recs if r.label == "NON_ORGANIC"),
            "by_source": {
                src: sum(1 for r in recs if r.dataset_source == src)
                for src in sorted({r.dataset_source for r in recs})
            },
        }
        for split, recs in splits.items()
    }
    with open(out_dir / "split_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    (out_dir.parent / "configs" / "split_seed.txt").parent.mkdir(parents=True, exist_ok=True)
    seed_file = out_dir.parent / "configs" / "split_seed.txt"
    seed_file.write_text(f"random_seed={seed}\n")
    print(f"[ok] manifest split ditulis ke {out_dir}, seed dicatat di {seed_file}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
