"""Serialization helpers for pipeline artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def write_delimited(path: str | Path, rows: list[dict], fieldnames: list[str], delimiter: str = ",") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_csv(path: str | Path, rows: list[dict], fieldnames: list[str]) -> None:
    write_delimited(path, rows, fieldnames, delimiter=",")


def write_tsv(path: str | Path, rows: list[dict], fieldnames: list[str]) -> None:
    write_delimited(path, rows, fieldnames, delimiter="\t")


def write_json(path: str | Path, payload: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
