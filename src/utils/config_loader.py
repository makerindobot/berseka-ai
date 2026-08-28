"""BERSEKA AI — Utility loader untuk configs/label_mapping.yaml dan training_config.yaml.

Single source of truth: JANGAN hardcode mapping label atau parameter training di
tempat lain. Semua modul (preprocessing, training, evaluasi, notebook Kaggle)
wajib load lewat modul ini.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"


@functools.lru_cache(maxsize=None)
def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_label_mapping(path: str | Path | None = None) -> dict[str, Any]:
    path = path or (CONFIGS_DIR / "label_mapping.yaml")
    return load_yaml(path)


def load_training_config(path: str | Path | None = None) -> dict[str, Any]:
    path = path or (CONFIGS_DIR / "training_config.yaml")
    return load_yaml(path)


def build_class_lookup(mapping: dict[str, Any], dataset_key: str) -> dict[str, str]:
    """Ubah section mapping dataset (mis. 'taco') jadi dict {nama_kelas_asal: TARGET}.

    Kelas yang tidak ditemukan akan dianggap 'DROP' oleh caller (lihat resolve_label).
    """
    section = mapping.get(dataset_key)
    if section is None:
        raise KeyError(
            f"Dataset key '{dataset_key}' tidak ada di label_mapping.yaml. "
            f"Key tersedia: {[k for k in mapping if isinstance(mapping[k], dict)]}"
        )
    lookup: dict[str, str] = {}
    for cls in section.get("organic", []):
        lookup[_norm(cls)] = "ORGANIC"
    for cls in section.get("non_organic", []):
        lookup[_norm(cls)] = "NON_ORGANIC"
    return lookup


def _norm(name: str) -> str:
    return name.strip().lower()


def resolve_label(mapping: dict[str, Any], dataset_key: str, raw_class_name: str) -> str | None:
    """Petakan nama kelas asal dataset -> 'ORGANIC' / 'NON_ORGANIC' / None (dibuang).

    Mengembalikan None bila kelas ada di `dropped_classes` global atau tidak dikenal
    sama sekali (fail-safe: lebih baik drop daripada salah label diam-diam).
    """
    dropped = {_norm(c) for c in mapping.get("dropped_classes", [])}
    if _norm(raw_class_name) in dropped:
        return None
    lookup = build_class_lookup(mapping, dataset_key)
    return lookup.get(_norm(raw_class_name))


CLASS_TO_ID = {"ORGANIC": 0, "NON_ORGANIC": 1}
ID_TO_CLASS = {v: k for k, v in CLASS_TO_ID.items()}
