"""Generate Q1 XML parse evidence from manifest-backed RDML fixtures."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.io.rdml_loader import extract_rdml_metadata, load_rdml


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "data" / "raw" / "manifest.csv"
    out_path = repo_root / "outputs" / "q1" / "xml_parse_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    included = [row for row in rows if row.get("status", "").strip().lower() == "included"]
    file_reports: list[dict] = []
    fatal_parse_errors = 0
    sha_mismatch_count = 0
    source_urls: set[str] = set()
    instruments: set[str] = set()

    for row in included:
        filename = row["file_name"].strip()
        source_urls.add(row.get("source_url", "").strip())
        file_path = manifest_path.parent / filename

        report = {
            "file_name": filename,
            "exists": file_path.exists(),
            "source_url": row.get("source_url", "").strip(),
            "sha256_expected": row.get("sha256", "").strip(),
        }
        if not file_path.exists():
            fatal_parse_errors += 1
            report["fatal_error"] = "missing_file"
            file_reports.append(report)
            continue

        actual_sha = sha256_file(file_path)
        report["sha256_actual"] = actual_sha
        report["sha256_match"] = actual_sha == report["sha256_expected"]
        if not report["sha256_match"]:
            sha_mismatch_count += 1

        try:
            metadata = extract_rdml_metadata(file_path)
            curve_rows = load_rdml(file_path)
            report["run_id"] = metadata["run_id"]
            report["instrument"] = metadata["instrument"]
            report["curve_row_count"] = len(curve_rows)
            instruments.add(metadata["instrument"])
        except ValueError as exc:
            fatal_parse_errors += 1
            report["fatal_error"] = str(exc)
        file_reports.append(report)

    checks = {
        "included_file_count": len(included),
        "distinct_source_count": len([value for value in source_urls if value]),
        "distinct_instrument_count": len([value for value in instruments if value]),
        "sha256_mismatch_count": sha_mismatch_count,
        "fatal_parse_errors": fatal_parse_errors,
    }

    checks["q1_pass"] = (
        checks["included_file_count"] >= 3
        and checks["distinct_source_count"] >= 3
        and checks["distinct_instrument_count"] >= 3
        and checks["sha256_mismatch_count"] == 0
        and checks["fatal_parse_errors"] == 0
    )

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest_path": "data/raw/manifest.csv",
        "checks": checks,
        "files": file_reports,
    }
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"q1_pass": checks["q1_pass"], "report": str(out_path.relative_to(repo_root))}))
    return 0 if checks["q1_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
