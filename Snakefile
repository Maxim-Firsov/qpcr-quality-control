from pathlib import Path

from src.workflow.manifest import validate_manifest


configfile: "workflow/config/batch_config.yaml"

OUTPUT_ROOT = Path(config["output_root"]).resolve()
VALIDATED_MANIFEST = OUTPUT_ROOT / "_workflow" / "validated_manifest.json"
GATE_CONFIG = Path(config.get("gate_config", "workflow/config/batch_config.yaml")).resolve()
MANIFEST_PAYLOAD = validate_manifest(
    config["manifest"],
    OUTPUT_ROOT,
    artifact_profile=config.get("artifact_profile", "review"),
)
RUN_IDS = [row["run_id"] for row in MANIFEST_PAYLOAD["rows"]]


rule all:
    input:
        str(OUTPUT_ROOT / "batch_master.json"),
        str(OUTPUT_ROOT / "batch_master.tsv"),
        str(OUTPUT_ROOT / "rerun_queue.csv"),
        str(OUTPUT_ROOT / "failure_reason_counts.tsv"),
        str(OUTPUT_ROOT / "batch_gate_status.json"),
        str(OUTPUT_ROOT / "batch_report.md"),


rule validate_manifest:
    output:
        str(VALIDATED_MANIFEST),
    params:
        manifest=config["manifest"],
        output_root=str(OUTPUT_ROOT),
        artifact_profile=config.get("artifact_profile", "review"),
    shell:
        "python -m src.workflow.manifest --manifest \"{params.manifest}\" --output-root \"{params.output_root}\" "
        "--artifact-profile {params.artifact_profile} --out \"{output}\""


rule run_manifest_row:
    input:
        validated_manifest=str(VALIDATED_MANIFEST),
    output:
        summary=str(OUTPUT_ROOT / "runs/{run_id}/summary.json"),
        workflow_status=str(OUTPUT_ROOT / "runs/{run_id}/workflow_status.json"),
    params:
        run_id="{run_id}",
    shell:
        "python -m src.workflow.batch_runner --validated-manifest \"{input.validated_manifest}\" --run-id {params.run_id}"


rule aggregate_batch:
    input:
        validated_manifest=str(VALIDATED_MANIFEST),
        summaries=expand(str(OUTPUT_ROOT / "runs/{run_id}/summary.json"), run_id=RUN_IDS),
        workflow_statuses=expand(str(OUTPUT_ROOT / "runs/{run_id}/workflow_status.json"), run_id=RUN_IDS),
    output:
        batch_master_json=str(OUTPUT_ROOT / "batch_master.json"),
        batch_master_tsv=str(OUTPUT_ROOT / "batch_master.tsv"),
        rerun_queue=str(OUTPUT_ROOT / "rerun_queue.csv"),
        failure_reason_counts=str(OUTPUT_ROOT / "failure_reason_counts.tsv"),
        batch_gate_status=str(OUTPUT_ROOT / "batch_gate_status.json"),
        batch_report=str(OUTPUT_ROOT / "batch_report.md"),
    params:
        output_root=str(OUTPUT_ROOT),
        gate_config=str(GATE_CONFIG),
    shell:
        "python -m src.workflow.aggregate_batch --validated-manifest \"{input.validated_manifest}\" "
        "--output-root \"{params.output_root}\" --gate-config \"{params.gate_config}\""
