"""Generate Q4 well-level QC outputs and synthetic failure evidence."""

from __future__ import annotations

import csv
import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli import run_pipeline


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    outdir = repo_root / "outputs" / "q4"
    outdir.mkdir(parents=True, exist_ok=True)

    run_pipeline(
        Namespace(
            curve_csv=str(repo_root / "data" / "fixtures" / "q4_curves.csv"),
            rdml=None,
            plate_meta_csv=str(repo_root / "data" / "fixtures" / "q4_plate_meta.csv"),
            outdir=str(outdir),
            min_cycles=3,
        )
    )

    well_calls = _read_csv_rows(outdir / "well_calls.csv")
    rerun_manifest = _read_csv_rows(outdir / "rerun_manifest.csv")
    rerun_rows = [row for row in well_calls if row["qc_status"] == "rerun"]

    explicit_reason_rows = sum(1 for row in rerun_manifest if row["rerun_reason"].strip() != "")
    check_report = {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": {
            "well_calls_exists": (outdir / "well_calls.csv").exists(),
            "rerun_manifest_exists": (outdir / "rerun_manifest.csv").exists(),
            "synthetic_failure_cases_detected": len(rerun_rows),
            "at_least_three_failure_cases": len(rerun_rows) >= 3,
            "rerun_decisions_have_explicit_reason": explicit_reason_rows == len(rerun_manifest),
        },
        "rerun_summary": {
            "rerun_rows": len(rerun_rows),
            "rerun_manifest_rows": len(rerun_manifest),
        },
    }
    check_report["checks"]["q4_pass"] = (
        check_report["checks"]["well_calls_exists"]
        and check_report["checks"]["rerun_manifest_exists"]
        and check_report["checks"]["at_least_three_failure_cases"]
        and check_report["checks"]["rerun_decisions_have_explicit_reason"]
    )

    check_path = outdir / "q4_check_report.json"
    check_path.write_text(json.dumps(check_report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"q4_pass": check_report["checks"]["q4_pass"], "report": str(check_path.relative_to(repo_root))}))
    return 0 if check_report["checks"]["q4_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
