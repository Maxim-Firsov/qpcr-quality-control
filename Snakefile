from pathlib import Path

from src.workflow.planning import planned_run_ids

configfile: "workflow/config/batch_config.yaml"

OUTPUT_ROOT = Path(config["output_root"]).resolve()
WORKFLOW_ROOT = OUTPUT_ROOT / "_workflow"
VALIDATED_MANIFEST = WORKFLOW_ROOT / "validated_manifest.json"
RUN_ROWS_DIR = WORKFLOW_ROOT / "run_rows"
MANIFEST_OK = WORKFLOW_ROOT / "manifest.ok"
GATE_CONFIG = Path(config.get("gate_config", "workflow/config/batch_release_policy.yaml")).resolve()

RUN_IDS = planned_run_ids(config["manifest"])
RUN_ROW_OUTPUTS = expand(str(RUN_ROWS_DIR / "{run_id}.json"), run_id=RUN_IDS)
RUN_SUMMARY_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/summary.json"), run_id=RUN_IDS)
RUN_STATUS_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/workflow_status.json"), run_id=RUN_IDS)
RUN_RERUN_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/rerun_manifest.csv"), run_id=RUN_IDS)
RUN_METADATA_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/run_metadata.json"), run_id=RUN_IDS)
RUN_PLATE_QC_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/plate_qc_summary.json"), run_id=RUN_IDS)
RUN_WELL_CALLS_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/well_calls.csv"), run_id=RUN_IDS)
RUN_REPORT_OUTPUTS = expand(str(OUTPUT_ROOT / "runs/{run_id}/report.html"), run_id=RUN_IDS)


rule all:
    input:
        str(OUTPUT_ROOT / "batch_master.json"),
        str(OUTPUT_ROOT / "batch_master.tsv"),
        str(OUTPUT_ROOT / "rerun_queue.csv"),
        str(OUTPUT_ROOT / "failure_reason_counts.tsv"),
        str(OUTPUT_ROOT / "batch_gate_status.json"),
        str(OUTPUT_ROOT / "batch_report.md"),
        RUN_SUMMARY_OUTPUTS,
        RUN_STATUS_OUTPUTS,
        RUN_RERUN_OUTPUTS,
        RUN_METADATA_OUTPUTS,
        RUN_PLATE_QC_OUTPUTS,
        RUN_WELL_CALLS_OUTPUTS,
        RUN_REPORT_OUTPUTS,


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


rule assert_manifest_valid:
    input:
        validated_manifest=str(VALIDATED_MANIFEST),
    output:
        str(MANIFEST_OK),
    shell:
        "python -m src.workflow.assert_manifest_valid --validated-manifest \"{input.validated_manifest}\" --out \"{output}\""


rule materialize_run_row:
    input:
        validated_manifest=str(VALIDATED_MANIFEST),
        manifest_ok=str(MANIFEST_OK),
    output:
        str(RUN_ROWS_DIR / "{run_id}.json"),
    params:
        run_id="{run_id}",
    shell:
        "python -m src.workflow.extract_run_row --validated-manifest \"{input.validated_manifest}\" "
        "--run-id {params.run_id} --out \"{output}\""


rule run_manifest_row:
    input:
        run_row=str(RUN_ROWS_DIR / "{run_id}.json"),
        manifest_ok=str(MANIFEST_OK),
    output:
        summary=str(OUTPUT_ROOT / "runs/{run_id}/summary.json"),
        workflow_status=str(OUTPUT_ROOT / "runs/{run_id}/workflow_status.json"),
        rerun_manifest=str(OUTPUT_ROOT / "runs/{run_id}/rerun_manifest.csv"),
        run_metadata=str(OUTPUT_ROOT / "runs/{run_id}/run_metadata.json"),
        plate_qc_summary=str(OUTPUT_ROOT / "runs/{run_id}/plate_qc_summary.json"),
        well_calls=str(OUTPUT_ROOT / "runs/{run_id}/well_calls.csv"),
        report_html=str(OUTPUT_ROOT / "runs/{run_id}/report.html"),
    shell:
        "python -m src.workflow.batch_runner --run-record \"{input.run_row}\""


rule aggregate_batch:
    input:
        validated_manifest=str(VALIDATED_MANIFEST),
        manifest_ok=str(MANIFEST_OK),
        run_rows=RUN_ROW_OUTPUTS,
        summaries=RUN_SUMMARY_OUTPUTS,
        workflow_statuses=RUN_STATUS_OUTPUTS,
        rerun_manifests=RUN_RERUN_OUTPUTS,
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
