"""BERSEKA AI — Remap anotasi YOLO TACO (60 kelas granular) -> skema biner
ORGANIC(0) / NON_ORGANIC(1), sesuai configs/label_mapping.yaml.

Input diasumsikan dataset vencerlanz09/taco-dataset-yolo-format, struktur umum:
  <root>/data.yaml        (berisi daftar nama kelas asli TACO, index sesuai label file)
  <root>/train/images, <root>/train/labels (txt YOLO: class_id cx cy w h)
  ... (val/test serupa, atau split flat images+labels — script mendeteksi otomatis)

Karena repo pihak ketiga rawan bug mapping index kelas, script ini:
  1. Selalu baca nama kelas dari data.yaml dataset asal (bukan asumsi urutan tetap)
  2. Petakan index_asal -> nama_kelas -> target biner via label_mapping.yaml
  3. Bbox milik kelas yang di-drop (mis. 'Other litter') dibuang dari file label
  4. Menyisakan log audit (jumlah bbox per kelas asal & per kelas target) untuk
     spot-check manual >=50 sample/kelas mayor sesuai rekomendasi dataset-decision.md §7.3
"""
from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path

import yaml

from src.utils.config_loader import CLASS_TO_ID, load_label_mapping, resolve_label


def read_taco_class_names(data_yaml_path: Path) -> list[str]:
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    names = spec.get("names")
    if isinstance(names, dict):
        # yolo data.yaml kadang pakai dict {0: 'name', ...}
        names = [names[i] for i in sorted(names.keys())]
    if not names:
        raise ValueError(f"Tidak menemukan 'names' di {data_yaml_path}")
    return names


def build_index_remap(class_names: list[str], mapping: dict, dataset_key: str = "taco") -> dict[int, int | None]:
    """index_asal -> target_id (0=ORGANIC, 1=NON_ORGANIC) atau None jika di-drop."""
    remap: dict[int, int | None] = {}
    unresolved: list[str] = []
    for idx, name in enumerate(class_names):
        target = resolve_label(mapping, dataset_key, name)
        if target is None:
            remap[idx] = None
        else:
            remap[idx] = CLASS_TO_ID[target]
        if target is None and name.strip().lower() not in {
            c.lower() for c in mapping.get("dropped_classes", [])
        }:
            unresolved.append(name)
    if unresolved:
        print(
            f"[warn] {len(unresolved)} kelas TACO tidak dikenal di label_mapping.yaml "
            f"(diperlakukan sbg drop, TAPI seharusnya ditambahkan eksplisit): {unresolved}"
        )
    return remap


def remap_label_file(src_txt: Path, dst_txt: Path, remap: dict[int, int | None], counter: Counter) -> int:
    """Tulis ulang 1 file label YOLO dengan class_id yang sudah dipetakan. Return jumlah bbox tersisa."""
    if not src_txt.exists():
        dst_txt.write_text("")
        return 0
    kept_lines = []
    for line in src_txt.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        orig_id = int(float(parts[0]))
        new_id = remap.get(orig_id)
        counter[f"orig_{orig_id}"] += 1
        if new_id is None:
            counter["dropped_bbox"] += 1
            continue
        counter[f"target_{new_id}"] += 1
        kept_lines.append(" ".join([str(new_id)] + parts[1:]))
    dst_txt.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""))
    return len(kept_lines)


def remap_taco_dataset(
    src_root: str | Path,
    dst_root: str | Path,
    splits: tuple[str, ...] = ("train", "valid", "val", "test"),
) -> dict:
    """Konversi seluruh dataset TACO YOLO ke skema biner. Menyalin images apa adanya,
    menulis ulang labels/, dan menghasilkan data.yaml baru berkelas 2.
    Mengembalikan ringkasan audit (counter bbox) untuk log/QA.
    """
    src_root = Path(src_root)
    dst_root = Path(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    data_yaml = src_root / "data.yaml"
    class_names = read_taco_class_names(data_yaml)
    mapping = load_label_mapping()
    remap = build_index_remap(class_names, mapping, dataset_key="taco")

    total_counter: Counter = Counter()
    found_splits = []
    for split in splits:
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists() or not lbl_dir.exists():
            continue
        found_splits.append(split)
        out_img_dir = dst_root / split / "images"
        out_lbl_dir = dst_root / split / "labels"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            out_lbl_path = out_lbl_dir / (img_path.stem + ".txt")
            n_kept = remap_label_file(lbl_path, out_lbl_path, remap, total_counter)
            if n_kept == 0:
                # gambar tanpa bbox valid setelah remap -> tetap disalin (background negative
                # sample berguna) tapi ditandai di counter untuk audit
                total_counter["images_zero_bbox_after_remap"] += 1
            shutil.copy2(img_path, out_img_dir / img_path.name)
            total_counter["images_total"] += 1

    new_data_yaml = {
        "path": str(dst_root),
        "train": "train/images" if "train" in found_splits else None,
        "val": "valid/images" if "valid" in found_splits else ("val/images" if "val" in found_splits else None),
        "test": "test/images" if "test" in found_splits else None,
        "nc": 2,
        "names": ["ORGANIC", "NON_ORGANIC"],
    }
    new_data_yaml = {k: v for k, v in new_data_yaml.items() if v is not None}
    with open(dst_root / "data.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(new_data_yaml, f, sort_keys=False, allow_unicode=True)

    summary = {
        "found_splits": found_splits,
        "class_names_original_count": len(class_names),
        "bbox_target_organic": total_counter.get("target_0", 0),
        "bbox_target_non_organic": total_counter.get("target_1", 0),
        "bbox_dropped": total_counter.get("dropped_bbox", 0),
        "images_total": total_counter.get("images_total", 0),
        "images_zero_bbox_after_remap": total_counter.get("images_zero_bbox_after_remap", 0),
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remap TACO YOLO labels -> ORGANIC/NON_ORGANIC")
    parser.add_argument("--src", required=True, help="Root dataset TACO YOLO asal")
    parser.add_argument("--dst", required=True, help="Root output dataset ter-remap")
    args = parser.parse_args()
    result = remap_taco_dataset(args.src, args.dst)
    print("=== Ringkasan remap TACO -> biner ===")
    for k, v in result.items():
        print(f"{k}: {v}")
