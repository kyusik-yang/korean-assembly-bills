"""Data loader -- reads parquet files, auto-downloading from GitHub on first use."""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd

_CACHE_DIR = Path.home() / ".cache" / "assembly-bills"
_REPO_RAW = "https://raw.githubusercontent.com/kyusik-yang/korean-assembly-bills/main/data"
_FILES = ["bills.parquet", "bill_texts.parquet", "proposers.parquet", "mp_metadata.parquet"]


def _download_data(dest: Path) -> None:
    """Download all parquet files from GitHub."""
    dest.mkdir(parents=True, exist_ok=True)
    total = len(_FILES)
    for i, fname in enumerate(_FILES, 1):
        target = dest / fname
        if target.exists():
            continue
        url = f"{_REPO_RAW}/{fname}"
        print(f"  downloading {fname} ({i}/{total})...", end=" ", flush=True)
        urllib.request.urlretrieve(url, target)
        size_mb = target.stat().st_size / 1024 / 1024
        print(f"{size_mb:.1f} MB", flush=True)


def _resolve_data_dir() -> Path:
    """Find the data directory. Search order:
    1. ASSEMBLY_BILLS_DATA env var
    2. ./data/ relative to CWD
    3. Relative to this file (editable install or running from repo)
    4. ~/.cache/assembly-bills/ (auto-downloaded)
    """
    # 1. Env var
    env = os.environ.get("ASSEMBLY_BILLS_DATA")
    if env:
        p = Path(env)
        if p.exists():
            return p

    # 2. CWD / data
    cwd_data = Path.cwd() / "data"
    if (cwd_data / "bills.parquet").exists():
        return cwd_data

    # 3. Relative to package (works for editable installs and running from repo)
    pkg_data = Path(__file__).resolve().parent.parent.parent / "data"
    if (pkg_data / "bills.parquet").exists():
        return pkg_data

    # 4. Auto-download to cache
    if (_CACHE_DIR / "bills.parquet").exists():
        return _CACHE_DIR

    print("assembly-bills: data not found locally. downloading from GitHub (~40 MB)...")
    _download_data(_CACHE_DIR)
    print("  done. cached at", _CACHE_DIR)
    return _CACHE_DIR


def load_bills(columns: Optional[list] = None) -> pd.DataFrame:
    """Load bill metadata (60,925 rows, 24 columns)."""
    return pd.read_parquet(_resolve_data_dir() / "bills.parquet", columns=columns)


def load_texts(columns: Optional[list] = None) -> pd.DataFrame:
    """Load propose-reason texts (60,925 rows)."""
    return pd.read_parquet(_resolve_data_dir() / "bill_texts.parquet", columns=columns)


def load_proposers(columns: Optional[list] = None) -> pd.DataFrame:
    """Load proposer records (769,773 rows)."""
    return pd.read_parquet(_resolve_data_dir() / "proposers.parquet", columns=columns)


def load_mp_metadata(columns: Optional[list] = None) -> pd.DataFrame:
    """Load MP metadata (947 rows: 661 unique MPs across 20th-22nd assemblies)."""
    return pd.read_parquet(_resolve_data_dir() / "mp_metadata.parquet", columns=columns)
