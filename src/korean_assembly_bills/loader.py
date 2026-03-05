"""Data loader -- reads parquet files from the repo or a configured path."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd


def _resolve_data_dir() -> Path:
    """Find the data directory. Search order:
    1. ASSEMBLY_BILLS_DATA env var
    2. ./data/ relative to CWD
    3. Relative to this file (editable install or running from repo)
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

    raise FileNotFoundError(
        "Data directory not found. Either:\n"
        "  1. Run from the repo root (where data/ is)\n"
        "  2. Set ASSEMBLY_BILLS_DATA=/path/to/data\n"
        "  3. git clone the repo first: git clone https://github.com/kyusik-yang/korean-assembly-bills"
    )


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
    """Load MP metadata (889 rows across 20th-22nd assemblies)."""
    return pd.read_parquet(_resolve_data_dir() / "mp_metadata.parquet", columns=columns)
