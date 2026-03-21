"""Batch-level aggregation and release gating for Snakemake workflow mode."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from src import __version__
from src.export.writers import write_csv, write_json, write_tsv


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_rerun_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def aggregate_batch(validated_manifest_path: str | Path, config_path: str | Path | None = None) -> dict:
    manifest_payload = _load_json(validated_manifest_path)
    config = _load_json(config_path) if config_path else {}
    thresholds = {
        "max_failed_runs_for_release": int(config.get("max_failed_runs_for_release", 0)),
        "max_rerun_wells_for_release": int(config.get("max_rerun_wells_for_release", 0)),
        "max_review_wells_for_release": int(config.get("max_review_wells_for_release", 0)),
        "max_review_runs_for_release": int(config.get("max_review_runs_for_release", 0)),
    }

    run_records = []
    rerun_queue = []
    reason_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"run_count": 0, "well_count": 0})
    global_counts = {
        "pass_wells": 0,
        "review_wells": 0,
        "rerun_wells": 0,
        "succeeded_runs": 0,
        "failed_runs": 0,
        "pass_runs": 0,
        "review_runs": 0,
        "rerun_runs": 0,
    }

    for row in manifest_payload["rows"]:
        run_dir = Path(row["run_dir"])
        summary = _load_json(run_dir / "summary.json")
        status = _load_json(run_dir / "workflow_status.json")
        execution_status = status["execution_status"]
        run_status = summary["run_status"]
        if execution_status == "succeeded":
            global_counts["succeeded_runs"] += 1
        else:
            global_counts["failed_runs"] += 1
            reason_totals["execution_failed"]["run_count"] += 1

        if run_status == "pass":
            global_counts["pass_runs"] += 1
        elif run_status == "review":
            global_counts["review_runs"] += 1
        elif run_status == "rerun":
            global_counts["rerun_runs"] += 1

        global_counts["pass_wells"] += int(summary["pass_count"])
        global_counts["review_wells"] += int(summary["review_count"])
        global_counts["rerun_wells"] += int(summary["rerun_count"])

        for item in summary.get("status_reason_counts", []):
            totals = reason_totals[item["reason"]]
            totals["run_count"] += 1
            totals["well_count"] += int(item["well_count"])

        rerun_rows = _load_rerun_rows(run_dir / "rerun_manifest.csv")
        for rerun_row in rerun_rows:
            rerun_queue.append(
                {
                    "batch_id": manifest_payload["batch_id"],
                    "run_id": row["run_id"],
                    "plate_id": rerun_row["plate_id"],
                    "well_id": rerun_row["well_id"],
                    "target_id": rerun_row["target_id"],
                    "sample_id": rerun_row["sample_id"],
                    "rerun_reason": rerun_row["rerun_reason"],
                    "evidence_score": rerun_row["evidence_score"],
                    "recommended_action": rerun_row["recommended_action"],
                }
            )

        run_records.append(
            {
                "run_id": row["run_id"],
                "execution_status": execution_status,
                "run_status": run_status,
                "artifact_dir": str(run_dir),
                "plate_count": int(summary["plate_count"]),
                "pass_count": int(summary["pass_count"]),
                "review_count": int(summary["review_count"]),
                "rerun_count": int(summary["rerun_count"]),
                "rerun_well_count": int(summary["rerun_well_count"]),
                "warning_count": int(summary["warning_count"]),
                "artifact_inventory": summary["artifact_inventory"],
            }
        )

    blocking_reasons = []
    review_reasons = []
    if global_counts["failed_runs"] > thresholds["max_failed_runs_for_release"]:
        blocking_reasons.append("execution_failures_present")
    if global_counts["rerun_wells"] > thresholds["max_rerun_wells_for_release"]:
        blocking_reasons.append("rerun_wells_present")
    if global_counts["review_wells"] > thresholds["max_review_wells_for_release"]:
        review_reasons.append("review_wells_present")
    if global_counts["review_runs"] > thresholds["max_review_runs_for_release"]:
        review_reasons.append("review_runs_present")

    release_status = "release"
    if blocking_reasons:
        release_status = "block"
    elif review_reasons:
        release_status = "review"

    reason_rows = [
        {
            "batch_id": manifest_payload["batch_id"],
            "failure_reason": reason,
            "run_count": totals["run_count"],
            "well_count": totals["well_count"],
        }
        for reason, totals in sorted(reason_totals.items())
    ]
    batch_master = {
        "schema_version": "v0.1.0",
        "generated_at_utc": _timestamp(),
        "batch_id": manifest_payload["batch_id"],
        "manifest_path": manifest_payload["manifest_path"],
        "manifest_sha256": manifest_payload["manifest_sha256"],
        "workflow_version": __version__,
        "artifact_profile": manifest_payload["artifact_profile"],
        "run_count": manifest_payload["run_count"],
        "release_status": release_status,
        "global_counts": global_counts,
        "failure_reason_totals": reason_rows,
        "runs": run_records,
    }
    batch_gate_status = {
        "schema_version": "v0.1.0",
        "generated_at_utc": batch_master["generated_at_utc"],
        "batch_id": manifest_payload["batch_id"],
        "release_status": release_status,
        "blocking_reasons": blocking_reasons,
        "review_reasons": review_reasons,
        "policy_thresholds": thresholds,
        "counts": global_counts,
    }
    batch_report_lines = [
        f"# Batch Report: {manifest_payload['batch_id']}",
        "",
        f"- Generated at: {batch_master['generated_at_utc']}",
        f"- Artifact profile: {manifest_payload['artifact_profile']}",
        f"- Release status: {release_status}",
        f"- Runs: {manifest_payload['run_count']}",
        f"- Failed runs: {global_counts['failed_runs']}",
        f"- Review wells: {global_counts['review_wells']}",
        f"- Rerun wells: {global_counts['rerun_wells']}",
        "",
        "## Gate Decision",
        "",
        f"- Blocking reasons: {', '.join(blocking_reasons) if blocking_reasons else 'none'}",
        f"- Review reasons: {', '.join(review_reasons) if review_reasons else 'none'}",
        "",
        "## Runs",
        "",
    ]
    for record in run_records:
        batch_report_lines.append(
            f"- {record['run_id']}: execution={record['execution_status']}, run_status={record['run_status']}, "
            f"review={record['review_count']}, rerun={record['rerun_count']}, artifact_dir={record['artifact_dir']}"
        )

    return {
        "batch_master": batch_master,
        "batch_gate_status": batch_gate_status,
        "rerun_queue": rerun_queue,
        "failure_reason_counts": reason_rows,
        "batch_report_md": "\n".join(batch_report_lines) + "\n",
    }


def write_batch_outputs(aggregated: dict, output_root: str | Path) -> None:
    output_root = Path(output_root)
    write_json(output_root / "batch_master.json", aggregated["batch_master"])
    write_tsv(
        output_root / "batch_master.tsv",
        [
            {
                "batch_id": aggregated["batch_master"]["batch_id"],
                "run_id": record["run_id"],
                "execution_status": record["execution_status"],
                "run_status": record["run_status"],
                "plate_count": record["plate_count"],
                "pass_count": record["pass_count"],
                "review_count": record["review_count"],
                "rerun_count": record["rerun_count"],
                "rerun_well_count": record["rerun_well_count"],
                "warning_count": record["warning_count"],
                "artifact_dir": record["artifact_dir"],
            }
            for record in aggregated["batch_master"]["runs"]
        ],
        [
            "batch_id",
            "run_id",
            "execution_status",
            "run_status",
            "plate_count",
            "pass_count",
            "review_count",
            "rerun_count",
            "rerun_well_count",
            "warning_count",
            "artifact_dir",
        ],
    )
    write_csv(
        output_root / "rerun_queue.csv",
        aggregated["rerun_queue"],
        [
            "batch_id",
            "run_id",
            "plate_id",
            "well_id",
            "target_id",
            "sample_id",
            "rerun_reason",
            "evidence_score",
            "recommended_action",
        ],
    )
    write_tsv(
        output_root / "failure_reason_counts.tsv",
        aggregated["failure_reason_counts"],
        ["batch_id", "failure_reason", "run_count", "well_count"],
    )
    write_json(output_root / "batch_gate_status.json", aggregated["batch_gate_status"])
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "batch_report.md").write_text(aggregated["batch_report_md"], encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate Snakemake batch outputs into release artifacts.")
    parser.add_argument("--validated-manifest", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--gate-config", required=False)
    args = parser.parse_args(argv)

    aggregated = aggregate_batch(args.validated_manifest, config_path=args.gate_config)
    write_batch_outputs(aggregated, args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
