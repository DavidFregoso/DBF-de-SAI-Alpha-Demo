from __future__ import annotations

from pathlib import Path
from typing import Iterable

from dbfread import DBF


DBF_EXTENSIONS = {".dbf", ".DBF"}


def list_dbf_files(folder: Path) -> list[Path]:
    return sorted([path for path in folder.iterdir() if path.suffix in DBF_EXTENSIONS])


def read_dbf(path: Path) -> list[dict]:
    table = DBF(path, load=True, char_decode_errors="ignore")
    return [dict(record) for record in table]


def sample_records(records: Iterable[dict], limit: int = 5) -> list[dict]:
    return list(records)[:limit]
