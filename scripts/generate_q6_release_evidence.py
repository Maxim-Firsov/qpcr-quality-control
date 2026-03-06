"""Generate Q6 validation and reproducibility evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
import tracemalloc
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli import run_pipeline

DETERMINISTIC_OUTPUTS = [
    "well_calls.csv",
    "rerun_manifest.csv",
    "plate_qc_summary.json",
    "run_metadata.json",
    "report.html",
]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_cmd(repo_root: Path, args: list[str]) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(args, cwd=str(repo_root), capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    return {
        "command": " ".join(args),
        "exit_code": proc.returncode,
        "runtime_seconds": round(elapsed, 6),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def _run_pipeline_once(repo_root: Path, outdir: Path) -> dict:
    tracemalloc.start()
    start = time.perf_counter()
    run_pipeline(
        Namespace(
            curve_csv=str(repo_root / "data" / "fixtures" / "q4_curves.csv"),
            rdml=None,
            plate_meta_csv=str(repo_root / "data" / "fixtures" / "q4_plate_meta.csv"),
            outdir=str(outdir),
            min_cycles=3,
        )
    )
    runtime = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"runtime_seconds": runtime, "peak_memory_mb": peak_bytes / (1024 * 1024)}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    out_root = repo_root / "outputs" / "q6"
    run_a = out_root / "run_a"
    run_b = out_root / "run_b"
    if out_root.exists():
        shutil.rmtree(out_root)
    run_a.mkdir(parents=True, exist_ok=True)
    run_b.mkdir(parents=True, exist_ok=True)
    (repo_root / ".pytest_tmp").mkdir(parents=True, exist_ok=True)

    test_results = [
        _run_cmd(repo_root, [sys.executable, "-m", "pytest", "tests/integration", "--basetemp", ".pytest_tmp/q6_integration"]),
        _run_cmd(repo_root, [sys.executable, "-m", "pytest", "tests/contract", "--basetemp", ".pytest_tmp/q6_contract"]),
    ]

    runtime_a = _run_pipeline_once(repo_root, run_a)
    runtime_b = _run_pipeline_once(repo_root, run_b)

    hash_rows = []
    deterministic_match = True
    for name in DETERMINISTIC_OUTPUTS:
        file_a = run_a / name
        file_b = run_b / name
        hash_a = _hash_file(file_a)
        hash_b = _hash_file(file_b)
        if hash_a != hash_b:
            deterministic_match = False
        hash_rows.append({"file": name, "run_a_sha256": hash_a, "run_b_sha256": hash_b, "match": hash_a == hash_b})

    checks = {
        "integration_tests_passed": test_results[0]["exit_code"] == 0,
        "contract_tests_passed": test_results[1]["exit_code"] == 0,
        "deterministic_artifact_hash_match": deterministic_match,
    }
    checks["q6_pass"] = all(checks.values())

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        },
        "checks": checks,
        "test_results": test_results,
        "pipeline_runs": {
            "run_a": {"runtime_seconds": round(runtime_a["runtime_seconds"], 6), "peak_memory_mb": round(runtime_a["peak_memory_mb"], 6)},
            "run_b": {"runtime_seconds": round(runtime_b["runtime_seconds"], 6), "peak_memory_mb": round(runtime_b["peak_memory_mb"], 6)},
        },
        "artifact_hashes": hash_rows,
    }

    out_path = out_root / "reproducibility_report.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"q6_pass": checks["q6_pass"], "report": str(out_path.relative_to(repo_root))}))
    return 0 if checks["q6_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
