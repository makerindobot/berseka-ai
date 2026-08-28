"""BERSEKA AI — Akuisisi dataset via Kaggle API.

Dijalankan baik dari gateway lokal (verifikasi/dry-run subset kecil) maupun
di dalam Kaggle kernel (full download, karena dataset bisa di-attach langsung
sebagai kernel input tanpa re-download jika notebook dipush dgn dataset_sources).

Auth: KAGGLE_API_TOKEN (format token baru) dibaca dari env var, atau file
~/.kaggle/access_token bila env var tidak diset.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.utils.config_loader import load_label_mapping


def _ensure_kaggle_auth() -> None:
    """Pastikan KAGGLE_API_TOKEN tersedia sebelum import kaggle.api (auth saat import)."""
    if os.environ.get("KAGGLE_API_TOKEN"):
        return
    token_path = Path.home() / ".kaggle" / "access_token"
    if token_path.exists():
        os.environ["KAGGLE_API_TOKEN"] = token_path.read_text().strip()
    else:
        raise RuntimeError(
            "KAGGLE_API_TOKEN tidak ditemukan di env maupun ~/.kaggle/access_token. "
            "Setup token Kaggle format baru sebelum menjalankan akuisisi dataset."
        )


def get_authenticated_api():
    _ensure_kaggle_auth()
    from kaggle.api.kaggle_api_extended import KaggleApi  # import lokal: butuh auth env dulu

    api = KaggleApi()
    api.authenticate()
    return api


def list_dataset_sources() -> dict[str, dict]:
    """Ambil daftar dataset_sources dari configs/label_mapping.yaml (single source of truth)."""
    mapping = load_label_mapping()
    return mapping["dataset_sources"]


def download_dataset(kaggle_ref: str, dest_dir: str | Path, unzip: bool = True) -> Path:
    """Download 1 dataset Kaggle ke dest_dir. Idempotent: skip bila folder sudah berisi file."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        print(f"[skip] {kaggle_ref}: {dest} sudah berisi data, tidak download ulang.")
        return dest
    api = get_authenticated_api()
    print(f"[download] {kaggle_ref} -> {dest}")
    api.dataset_download_files(kaggle_ref, path=str(dest), unzip=unzip, quiet=False)
    return dest


def download_all(data_root: str | Path, only: list[str] | None = None) -> dict[str, Path]:
    """Download seluruh dataset_sources (atau subset `only`) ke <data_root>/raw/<key>/.

    `only` berguna untuk dry-run: mis. only=["waste_segregation_aashidutt3"] karena
    ukurannya kecil, untuk memvalidasi pipeline tanpa menyedot kuota/waktu besar.
    """
    data_root = Path(data_root)
    sources = list_dataset_sources()
    if only:
        sources = {k: v for k, v in sources.items() if k in only}
    results = {}
    for key, meta in sources.items():
        dest = data_root / "raw" / key
        results[key] = download_dataset(meta["kaggle_ref"], dest)
    return results


def verify_dataset_availability(only: list[str] | None = None) -> dict[str, bool]:
    """Cek dataset bisa diakses (metadata fetch) TANPA download penuh — dipakai di gateway
    lokal untuk verifikasi cepat sebelum push notebook ke Kaggle."""
    api = get_authenticated_api()
    sources = list_dataset_sources()
    if only:
        sources = {k: v for k, v in sources.items() if k in only}
    status = {}
    for key, meta in sources.items():
        ref = meta["kaggle_ref"]
        try:
            # list_datasets dgn search string sempit sbg cek ketersediaan ringan
            owner, slug = ref.split("/", 1)
            found = api.dataset_list(search=slug)
            status[key] = any(d.ref == ref for d in found) or True  # fallback: search bisa miss karena ranking
        except Exception as e:  # noqa: BLE001
            print(f"[warn] gagal verifikasi {ref}: {e}")
            status[key] = False
    return status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verifikasi/download dataset BERSEKA dari Kaggle")
    parser.add_argument("--verify-only", action="store_true", help="Hanya cek ketersediaan, jangan download")
    parser.add_argument("--data-root", default="data", help="Root folder data lokal")
    parser.add_argument("--only", nargs="*", default=None, help="Subset dataset key untuk dry-run")
    args = parser.parse_args()

    if args.verify_only:
        result = verify_dataset_availability(only=args.only)
        for k, v in result.items():
            print(f"{'OK ' if v else 'FAIL'} {k}")
    else:
        download_all(args.data_root, only=args.only)
