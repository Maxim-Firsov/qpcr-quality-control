# IO Contract (v0.1.0)

## Execution Modes

Single-run CLI modes:

- `--rdml <path-or-directory>`
- `--curve-csv <path>`

Optional single-run inputs:

- `--plate-meta-csv <path>`
- `--control-map-config <path>`
- `--normalization-config <path>`
- `--normalization-profile <name|auto>`
- `--artifact-profile <minimal|review|full>`
- `--run-id <stable-id>`

Workflow-mode batch execution:

- entrypoint: `Snakefile`
- manifest format: TSV
- required columns: `run_id`, `input_mode`, `input_path`
- optional columns:
  - `plate_meta_csv`
  - `control_map_config`
  - `min_cycles`
  - `plate_schema`
  - `allow_empty_run`
  - `confidence_threshold`
  - `late_ct_threshold`
  - `low_signal_threshold`
  - `replicate_ct_spread_threshold`
  - `replicate_ct_outlier_threshold`
  - `normalization_profile`
  - `normalization_config`

Workflow behavior:

1. validate the manifest before dispatch
2. assign each row a stable run directory under `output_root/runs/<run_id>`
3. execute the CLI once per manifest row
4. preserve per-run summary artifacts even when a run fails
5. aggregate batch-level handoff artifacts from compact machine-readable outputs

Legacy sequential manifest mode:

- `--batch-manifest <csv-path>`
- retained for compatibility
- not the primary production batch path

## Canonical Curve Schema

Required columns:

- `run_id`
- `plate_id`
- `well_id`
- `sample_id`
- `target_id`
- `cycle`
- `fluorescence`

Optional columns:

- `is_melt_stage`
- `temperature_c`
- `instrument`

Parser path to canonical schema:

1. `src/io/rdml_loader.py` parses RDML XML or ZIP-container RDML into canonical rows.
2. `src/core/normalize.py` standardizes identifiers and numeric fields.
3. `src/core/validate.py` enforces schema, cycle monotonicity, geometry rules, and melt-stage exclusion.
4. `src/core/features.py` applies assay- and instrument-aware normalization profiles and derivative features.
5. `src/core/melt_qc.py` turns melt-stage rows into reviewable specificity signals recorded in outputs.

`--plate-meta-csv` optional columns:

- required: `plate_id`, `well_id`, `control_type`
- optional: `expected_target_id`, `replicate_group`, `sample_group`

`--control-map-config` JSON shape:

- top-level key: `rules`
- each rule can include:
  - `plate_id` (`*` allowed)
  - `target_id` (`*` allowed)
  - `well_ids` (list)
  - `control_type`
  - `expected_target_id`
  - `replicate_group`
  - `sample_group`

## Per-Run Outputs

Always-on compact outputs:

- `summary.json`
- `run_metadata.json`
- `plate_qc_summary.json`
- `rerun_manifest.csv`

Conditional outputs:

- `well_calls.csv`
- `report.html`

Artifact profile behavior:

- `minimal`: compact outputs for every run; no `report.html`; `well_calls.csv` only for `rerun` runs
- `review`: compact outputs for every run; `well_calls.csv` and `report.html` only for `review` or `rerun` runs
- `full`: all per-run outputs for every run

`summary.json` required keys:

- `schema_version`
- `generated_at_utc`
- `run_id`
- `execution_status`
- `execution_mode`
- `plate_schema`
- `artifact_profile`
- `run_status`
- `plate_count`
- `pass_count`
- `review_count`
- `rerun_count`
- `rerun_well_count`
- `warning_count`
- `warnings`
- `status_reason_counts`
- `counts`
- `global_counts`
- `timing_seconds`
- `peak_memory_mb`
- `warning_codes`
- `artifact_inventory`

`well_calls.csv` required columns:

- `run_id`
- `plate_id`
- `well_id`
- `sample_id`
- `target_id`
- `control_type`
- `ct_estimate`
- `hmm_state_path_compact`
- `amplification_confidence`
- `call_label`
- `qc_status`
- `qc_flags`

`rerun_manifest.csv` required columns:

- `plate_id`
- `well_id`
- `target_id`
- `sample_id`
- `rerun_reason`
- `evidence_score`
- `recommended_action`

`plate_qc_summary.json` required top-level keys:

- `schema_version`
- `generated_at_utc`
- `plates`
- `global_counts`

`run_metadata.json` required keys:

- `schema_version`
- `tool_version`
- `run_id`
- `execution_mode`
- `plate_schema`
- `artifact_profile`
- `inputs`
- `input_hashes`
- `input_snapshot_date`
- `record_counts`
- `model_config`
- `normalization`
- `control_map`
- `melt_qc`
- `data_validation_summary`
- `qc_thresholds`
- `timing_seconds`
- `stage_timings_seconds`
- `peak_memory_mb`
- `warnings`
- `warning_codes`
- `artifact_inventory`

`report.html` major sections:

- Overview
- Per-Plate Summary
- Plate Heatmaps
- Plate Alerts
- Top Flagged Wells
- Curve Drilldowns
- Rerun Rationale

## Batch Outputs

Workflow mode writes:

- `batch_master.json`
- `batch_master.tsv`
- `rerun_queue.csv`
- `failure_reason_counts.tsv`
- `batch_gate_status.json`
- `batch_report.md`

`batch_master.json` required top-level keys:

- `schema_version`
- `generated_at_utc`
- `batch_id`
- `manifest_path`
- `manifest_sha256`
- `workflow_version`
- `artifact_profile`
- `run_count`
- `release_status`
- `global_counts`
- `failure_reason_totals`
- `runs`

Each `runs[]` object includes:

- `run_id`
- `execution_status`
- `run_status`
- `artifact_dir`
- `plate_count`
- `pass_count`
- `review_count`
- `rerun_count`
- `rerun_well_count`
- `warning_count`
- `artifact_inventory`

`batch_master.tsv` required columns:

- `batch_id`
- `run_id`
- `execution_status`
- `run_status`
- `plate_count`
- `pass_count`
- `review_count`
- `rerun_count`
- `rerun_well_count`
- `warning_count`
- `artifact_dir`

`rerun_queue.csv` required columns:

- `batch_id`
- `run_id`
- `plate_id`
- `well_id`
- `target_id`
- `sample_id`
- `rerun_reason`
- `evidence_score`
- `recommended_action`

`failure_reason_counts.tsv` required columns:

- `batch_id`
- `failure_reason`
- `run_count`
- `well_count`

`batch_gate_status.json` required keys:

- `schema_version`
- `generated_at_utc`
- `batch_id`
- `release_status`
- `blocking_reasons`
- `review_reasons`
- `policy_thresholds`
- `counts`

Output contract coverage is enforced by:

- `tests/contract/test_output_contract.py`
- `tests/contract/test_schema_compatibility.py`
- `tests/integration/test_snakemake_workflow.py`
