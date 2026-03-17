# IO Contract (v0.1.0)

## Input Modes

Primary mode (production path):

- `--rdml <path-or-directory>`
- if directory is provided, all `*.rdml` files are ingested
- each RDML file is parsed to canonical rows before downstream normalization/validation

Secondary mode (adapter/testing path):

- `--curve-csv <path>`
- `--control-map-config <path>` optional JSON rules for assay/control layouts

Batch mode:

- `--batch-manifest <csv-path>`
- required manifest columns:
  - `input_mode` (`rdml` or `curve_csv`)
  - `input_path`
- optional manifest columns:
  - `outdir`
  - `plate_meta_csv`
  - `min_cycles`
  - `plate_schema`
  - `allow_empty_run`

CLI QC threshold overrides:

- `--confidence-threshold <float>`
- `--late-ct-threshold <float>`
- `--low-signal-threshold <float>`
- `--replicate-ct-spread-threshold <float>`
- `--replicate-ct-outlier-threshold <float>`
- `--normalization-profile <name|auto>`
- `--normalization-config <path>`

Canonical row schema required columns:

- `run_id`
- `plate_id`
- `well_id`
- `sample_id`
- `target_id`
- `cycle`
- `fluorescence`

Optional:

- `is_melt_stage`
- `temperature_c`

Parser path to canonical schema:

1. `src/io/rdml_loader.py` (`load_rdml`) parses RDML XML into canonical rows.
2. `src/core/normalize.py` enforces normalized IDs and typed cycle/fluorescence fields.
3. `src/core/validate.py` applies schema/well/cycle guards, excludes rows marked as melt stage, and produces rejection summaries.
4. `src/core/features.py` resolves assay/instrument-aware normalization profiles before derivative feature generation.
5. `src/core/melt_qc.py` summarizes excluded melt-stage rows into specificity-review signals recorded in metadata and QC flags.

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

## Outputs

The pipeline writes:

- `well_calls.csv`
- `rerun_manifest.csv`
- `plate_qc_summary.json`
- `run_metadata.json`
- `summary.json`
- `report.html`

`report.html` major sections:

- Overview
- Per-Plate Summary
- Plate Heatmaps
- Plate Alerts
- Top Flagged Wells
- Curve Drilldowns
- Rerun Rationale

Output contract is enforced by `tests/contract/test_output_contract.py`.

`run_metadata.json` also records:

- `normalization.requested_profile`
- `normalization.config_path`
- `normalization.config_sha256`
- `control_map.config_path`
- `control_map.config_sha256`
- `melt_qc.well_target_count`
- `melt_qc.review_count`
