# qpcr-quality-control

[![CI](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml)

Deterministic qPCR quality control for RDML and canonical curve CSV inputs.

`qpcr-quality-control` is a command-line tool for reviewing amplification traces, applying explicit QC rules, and writing auditable outputs for downstream review or workflow gating. The project is designed for transparent rule-based behavior: thresholds, control logic, normalization choices, and escalation reasons are visible in the outputs rather than hidden behind opaque instrument software.

The repository now has two operational layers:

- single-run CLI mode for one RDML file, one RDML directory, or one canonical curve CSV analysis
- Snakemake batch mode for manifest-driven dispatch, resumability, selective artifact generation, rerun consolidation, and final batch handoff packets

## What It Does

- ingests RDML files, including plain XML and ZIP-container `.rdml` files
- ingests canonical per-cycle CSV files for testing, adapters, and workflow integration
- decodes amplification trajectories with deterministic forward-only Viterbi state calling
- estimates Ct from adjusted amplification curves
- applies QC rules for NTC contamination, replicate discordance, positive-control failure, late amplification, low-signal curves, edge-well review, melt-curve review, and replicate Ct spread/outliers
- supports assay- and instrument-aware normalization profiles
- supports metadata-driven and config-driven control layouts
- writes machine-readable CSV and JSON outputs plus an HTML review report
- supports policy-driven non-zero exits for automation and pipeline gating

## Intended Use

This tool is intended for:

- local qPCR run review
- automated QC steps before downstream analysis
- assay development and workflow prototyping
- adapter and contract testing against canonical curve inputs

This tool is not presented as a diagnostic device, clinical interpretation engine, or substitute for assay-specific laboratory validation.

## Installation

Python `3.10+` is required.

Editable install:

```powershell
python -m pip install -e .
```

Standard install from a clone:

```powershell
python -m pip install .
```

Install workflow support for Snakemake batch release mode:

```powershell
python -m pip install -e .[workflow]
```

If the installed `qpcr-quality-control` script is not on your `PATH`, invoke the CLI with:

```powershell
python -m src.cli --help
```

## Quick Start

Run the bundled public demo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_public_demo.ps1 -Fixture stepone_std.rdml -PlateSchema 96
```

Primary review artifacts:

- `outputs/demo_stepone_std/summary.json`
- `outputs/demo_stepone_std/run_metadata.json`
- `outputs/demo_stepone_std/well_calls.csv`
- `outputs/demo_stepone_std/report.html`

Run the bundled Snakemake batch demo:

```powershell
python -m snakemake --snakefile Snakefile --cores 1 --configfile workflow\config\batch_config.yaml
```

The shipped workflow config files in `workflow\config\` use standard YAML syntax.

Primary batch handoff artifacts:

- `outputs/snakemake_demo_batch/batch_master.json`
- `outputs/snakemake_demo_batch/batch_master.tsv`
- `outputs/snakemake_demo_batch/rerun_queue.csv`
- `outputs/snakemake_demo_batch/failure_reason_counts.tsv`
- `outputs/snakemake_demo_batch/batch_gate_status.json`
- `outputs/snakemake_demo_batch/batch_report.md`

## Common Usage

RDML input:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\run_rdml --min-cycles 25 --plate-schema 96
```

RDML directory input:

```powershell
python -m src.cli --rdml data\raw --outdir outputs\run_rdml_batch --min-cycles 25 --plate-schema auto
```

Canonical CSV input with plate metadata:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --plate-meta-csv data\fixtures\q4_plate_meta.csv --outdir outputs\run_csv --min-cycles 3 --plate-schema 96
```

Control-map driven layout:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --control-map-config config\control_map.example.json --outdir outputs\run_control_map --min-cycles 3 --plate-schema 96
```

Normalization profile override:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\run_profiled --plate-schema 96 --normalization-profile roche_lc480_standard
```

QC threshold override:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\run_thresholds --min-cycles 25 --plate-schema 96 --confidence-threshold 0.7 --late-ct-threshold 33 --low-signal-threshold 0.2
```

Artifact profile override for direct CLI use:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\run_review_profile --plate-schema 96 --artifact-profile review
```

Snakemake batch mode:

```powershell
python -m snakemake --snakefile Snakefile --cores 1 --configfile workflow\config\batch_config.yaml
```

Workflow gating:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-review
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-rerun
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-edge-alert
```

## Why Snakemake Is Needed

The CLI is the per-run analysis engine. It should stay focused on deterministic ingestion, state calling, QC logic, and run-level serialization.

Snakemake becomes necessary when the operating unit is a batch rather than a single plate review. In that mode we need:

- manifest preflight validation before dispatch
- stable run directories so finished runs are not recomputed after interruptions
- selective artifact policies so passing runs do not emit heavyweight reviewer artifacts by default
- normalized batch aggregation that reads compact machine-readable outputs instead of scraping HTML
- batch-level release, review, and block decisions plus a final handoff packet for the lab or analyst queue

That is the gap the workflow layer fills.

Workflow preflight is also explicit:

- `validate_manifest` writes `output_root\_workflow\validated_manifest.json`
- `assert_manifest_valid` stops the workflow before run dispatch if that artifact reports `validation_status=invalid`
- invalid manifests therefore leave a reviewable validation artifact behind instead of failing during Snakefile import

## Inputs

Supported execution modes:

- `--rdml <file-or-directory>`
- `--curve-csv <file>`

Workflow-mode batch input:

- `workflow/manifests/*.tsv` consumed by `Snakefile`
- required manifest columns: `run_id`, `input_mode`, `input_path`
- optional manifest columns: `plate_meta_csv`, `control_map_config`, `min_cycles`, `plate_schema`, `allow_empty_run`, threshold overrides, and normalization overrides

Legacy sequential manifest mode remains available through `--batch-manifest <file>`, but the production batch path is the Snakemake workflow.

Optional supporting inputs:

- `--plate-meta-csv <file>`
- `--control-map-config <file>`
- `--normalization-config <file>`
- `--artifact-profile <minimal|review|full>`

Canonical curve CSV expected columns:

- `run_id`
- `plate_id`
- `well_id`
- `sample_id`
- `target_id`
- `cycle`
- `fluorescence`

Optional canonical columns:

- `temperature_c`
- `is_melt_stage`
- `instrument`

Plate metadata CSV supports:

- required: `plate_id`, `well_id`, `control_type`
- optional: `expected_target_id`, `replicate_group`, `sample_group`

Control-map JSON supports rules with:

- `plate_id`
- `target_id`
- `well_ids`
- `control_type`
- `expected_target_id`
- `replicate_group`
- `sample_group`

Detailed contract documentation is in [docs/io_contract.md](docs/io_contract.md).

## Outputs

Single-run CLI default behavior uses `--artifact-profile full`, so every per-run artifact is emitted:

- `summary.json`
- `run_metadata.json`
- `plate_qc_summary.json`
- `rerun_manifest.csv`
- `well_calls.csv`
- `report.html`

Batch Snakemake mode defaults to `review` profile and treats artifacts in tiers:

- always-on compact outputs: `summary.json`, `run_metadata.json`, `plate_qc_summary.json`, `rerun_manifest.csv`
- tracked reviewer-facing artifacts: `well_calls.csv`, `report.html`
- batch packet outputs: `batch_master.json`, `batch_master.tsv`, `rerun_queue.csv`, `failure_reason_counts.tsv`, `batch_gate_status.json`, `batch_report.md`

Artifact profile behavior:

- `minimal`: always writes compact per-run outputs and batch outputs; reviewer-facing artifacts are only populated with full content for rerun runs, but workflow mode still tracks their paths for recovery
- `review`: default workflow mode; writes compact per-run outputs for every run, generates rich `well_calls.csv` plus `report.html` for `review` or `rerun` runs, and may recreate lightweight placeholders for non-flagged runs so Snakemake can detect missing tracked artifacts
- `full`: writes all per-run outputs for every run

Recommended first-read artifacts:

- `summary.json` for automation, run status, artifact inventory, and fast status checks
- `well_calls.csv` for well-level review
- `report.html` for human review
- `run_metadata.json` for audit, provenance, thresholds, and runtime context
- `batch_master.json` as the canonical batch deliverable in workflow mode
- `batch_master.tsv` as the spreadsheet-friendly batch companion

`run_metadata.json` records:

- run identifier and artifact profile
- input paths and hashes
- validation summary
- QC thresholds used
- normalization config details
- control-map config details
- melt-QC summary counts
- runtime and stage timings
- peak traced memory
- warnings and warning codes

`summary.json` records:

- `run_id`
- `execution_status`
- `run_status`
- `artifact_profile`
- pass/review/rerun counts
- warning inventory
- status-reason counts
- artifact inventory

Workflow-mode batch outputs are aggregated from compact machine-readable artifacts and do not depend on `report.html`.

`report.html` includes:

- overview counts
- per-plate summary
- plate heatmaps
- plate alerts
- top flagged wells
- curve drilldowns for flagged wells
- rerun rationale

## Public Fixtures

Bundled public RDML fixtures:

| Fixture | Purpose |
|---|---|
| `stepone_std.rdml` | ZIP-container RDML parsing and small end-to-end run |
| `BioRad_qPCR_melt.rdml` | archived RDML parsing and melt-stage temperature capture |
| `lc96_bACTXY.rdml` | larger workload and numeric react-to-well mapping |

Optional local comparison material:

- `data\raw\PCRedux_1.2-1.tar.gz`

If the optional PCRedux tarball is present, the bundled demo script can also write:

- `outputs/demo_stepone_std/pcrredux_compare.json`

Direct comparison command:

```powershell
python scripts\compare_pcrredux.py --well-calls outputs\demo_stepone_std\well_calls.csv --fixture stepone_std --pcrredux-tarball data\raw\PCRedux_1.2-1.tar.gz --out outputs\demo_stepone_std\pcrredux_compare.json
```

## Validation and Reproducibility

The repository includes:

- unit tests
- integration tests
- contract tests
- deterministic reproducibility checks
- public-fixture parser and runtime coverage

Primary references:

- [VALIDATION.md](VALIDATION.md)
- [RESULTS.md](RESULTS.md)
- [docs/data_sources.md](docs/data_sources.md)
- [docs/io_contract.md](docs/io_contract.md)
- [docs/workflow_mode.md](docs/workflow_mode.md)

Quality checks used in development:

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\deep_sweep.ps1
```

## Performance

Current public spot benchmarks are documented in [RESULTS.md](RESULTS.md).

At the documented baseline:

- `stepone_std.rdml`: about `0.06s`
- `BioRad_qPCR_melt.rdml`: about `0.13s`
- `lc96_bACTXY.rdml`: about `1.23s`

These measurements are development-machine observations, not platform-wide guarantees.

## Limitations

- current QC logic is deterministic and rule-based; it is not statistically calibrated against large external truth sets
- public RDML fixtures support parser and runtime evidence, not biological ground truth claims
- melt-curve review is heuristic specificity review and does not replace assay-specific laboratory validation
- normalization profiles are configuration-driven approximations, not instrument vendor calibrations
- broad vendor compatibility should not be assumed beyond the covered fixtures and tests
- this project does not claim clinical sensitivity, specificity, or regulatory suitability

## Repository Layout

- `src/` implementation
- `workflow/` Snakemake config and manifest examples
- `Snakefile` batch orchestration entrypoint
- `tests/` unit, integration, and contract coverage
- `data/raw/` RDML fixtures and provenance manifest
- `data/fixtures/` synthetic validation fixtures
- `docs/` contracts, architecture, and data-source notes
- `scripts/` demo, comparison, and verification utilities
- `config/` model and normalization/control-map configuration

## Contributing

Contributions that improve parser coverage, fixture quality, contract clarity, testing, and documentation are welcome.

Before opening a change, run:

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\deep_sweep.ps1
```

When reporting issues, include:

- command used
- input mode and fixture details
- expected behavior
- observed behavior
- relevant output files or warning codes

## License

MIT. See `LICENSE`.
