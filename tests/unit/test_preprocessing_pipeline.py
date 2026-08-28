"""Unit test ringan untuk pipeline preprocessing BERSEKA AI (tidak butuh GPU/torch)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.preprocessing.split_dataset import SampleRecord, group_aware_stratified_split
from src.utils.config_loader import CLASS_TO_ID, load_label_mapping, resolve_label


def test_label_mapping_resolves_known_classes():
    mapping = load_label_mapping()
    assert resolve_label(mapping, "taco", "Food waste") == "ORGANIC"
    assert resolve_label(mapping, "taco", "Clear plastic bottle") == "NON_ORGANIC"
    assert resolve_label(mapping, "taco", "Other litter") is None
    assert resolve_label(mapping, "realwaste", "Vegetation") == "ORGANIC"
    assert resolve_label(mapping, "garbage_classification_v2", "biological") == "ORGANIC"
    assert resolve_label(mapping, "waste_segregation_aashidutt3", "Biodegradable") == "ORGANIC"


def test_class_to_id_binary_scheme():
    assert CLASS_TO_ID == {"ORGANIC": 0, "NON_ORGANIC": 1}


def test_split_has_no_group_leakage():
    records = []
    for src in ["taco", "realwaste"]:
        for label in ["ORGANIC", "NON_ORGANIC"]:
            for i in range(30):
                grp = f"{src}_{label}_grp{i // 3}"
                records.append(
                    SampleRecord(path=f"/data/{src}/{label}/{i}.jpg", label=label, dataset_source=src, group_id=grp)
                )
    splits = group_aware_stratified_split(records, seed=42)
    from collections import defaultdict

    group_to_splits = defaultdict(set)
    for split_name, recs in splits.items():
        for r in recs:
            group_to_splits[r.group_id].add(split_name)
    leaked = {g: s for g, s in group_to_splits.items() if len(s) > 1}
    assert not leaked, f"Data leakage terdeteksi pada grup: {leaked}"
    assert len(splits["train"]) > 0 and len(splits["val"]) > 0 and len(splits["test"]) > 0


if __name__ == "__main__":
    test_label_mapping_resolves_known_classes()
    test_class_to_id_binary_scheme()
    test_split_has_no_group_leakage()
    print("[ok] semua unit test preprocessing lulus")
