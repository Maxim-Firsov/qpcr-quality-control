# IO Contract (v0.1.0 scaffold)

## Input (supported now)

`--curve-csv` canonical schema required columns:

- `run_id`
- `plate_id`
- `well_id`
- `sample_id`
- `target_id`
- `cycle`
- `fluorescence`

Optional:

- `is_melt_stage`

`--plate-meta-csv` optional columns:

- required: `plate_id`, `well_id`, `control_type`

## Outputs

The pipeline writes:

- `well_calls.csv`
- `rerun_manifest.csv`
- `plate_qc_summary.json`
- `run_metadata.json`
- `report.html`

Output contract is enforced by `tests/contract/test_output_contract.py`.
