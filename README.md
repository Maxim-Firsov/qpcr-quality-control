# qpcr-quality-control

[![CI](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml)

`qpcr-quality-control` is a deterministic local quality-control pipeline for qPCR amplification curves.
It ingests RDML or canonical curve CSV, performs fast forward-only Viterbi state decoding, applies
lightweight QC rules, and emits auditable CSV/JSON/HTML outputs without requiring hosted services.

The project is positioned as an explainable, reproducible portfolio-grade pipeline prototype rather
than a clinically validated production system.

## Quick Review Path

1. Run the public demo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_public_demo.ps1 -Fixture stepone_std.rdml -PlateSchema 96
```

2. Inspect the compact orchestration artifact:

- `outputs/demo_stepone_std/summary.json`

3. Inspect the reviewer-facing report:

- `outputs/demo_stepone_std/report.html`

4. Inspect the public-reference comparison output when `PCRedux_1.2-1.tar.gz` is present locally:

- `outputs/demo_stepone_std/pcrredux_compare.json`

## Features

- RDML and canonical CSV input support
- Plate metadata joins tolerate common well-ID formats such as `A1` and `A01`
- Supports both plain XML `.rdml` files and ZIP-container RDML archives from public example datasets
- Captures per-cycle temperature when present and excludes rows explicitly marked as melt-stage observations
- Deterministic forward-only Viterbi state decoding with locked model configuration
- Ct estimation from adjusted amplification curves
- QC rules for NTC contamination, replicate discordance, positive-control failure, late amplification, low-signal curves, and edge-well review
- Plate-level summary with geometry-aware edge-effect alerting for `96`, `384`, or `auto` mode
- Static HTML report plus auditable run metadata with input hashes and measured runtime
- `run_metadata.json` now records both runtime and peak traced memory
- Unit, integration, and contract tests with a lightweight runtime benchmark fixture

## Scope and Constraints

- Runs locally on small public fixtures and synthetic validation data
- Optimized for fast laptop execution and simple dependency footprint
- Does not claim clinical sensitivity/specificity or production-lab validation
- Keeps bundled data small so repository clone/download size stays practical

## Repository Layout

- `src/` pipeline implementation
- `tests/` unit, integration, and output-contract tests
- `data/raw/` RDML fixtures and manifest
- `data/fixtures/` synthetic QC validation fixture set
- `docs/` architecture, IO contract, and source provenance

## Installation

```powershell
python -m pip install -e .
```

## Usage

Run on RDML input:

```powershell
python -m src.cli --rdml data\raw --outdir outputs\run_rdml --min-cycles 25 --plate-schema auto
```

Run on canonical CSV input:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --plate-meta-csv data\fixtures\q4_plate_meta.csv --outdir outputs\run_csv --min-cycles 3 --plate-schema 96
```

By default the CLI fails with a non-zero exit if validation rejects every well-target curve. Use `--allow-empty-run` only when your surrounding workflow explicitly wants empty-but-audited outputs from fully rejected inputs.

Use `--plate-schema 96` or `--plate-schema 384` when your workflow knows the plate format. `auto` infers the smallest standard geometry that fits the observed well IDs.

Policy-driven pipeline gating:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-review
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-rerun
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-edge-alert
```

Threshold overrides:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\tuned_run --min-cycles 25 --confidence-threshold 0.7 --late-ct-threshold 33 --low-signal-threshold 0.2
```

Batch manifest mode:

```powershell
python -m src.cli --batch-manifest batch_runs.csv --outdir outputs\batch
```

The batch manifest is a CSV with rows such as:

```csv
input_mode,input_path,outdir,min_cycles,plate_schema,allow_empty_run,plate_meta_csv
curve_csv,data\fixtures\q4_curves.csv,outputs\batch_run_001,3,96,false,data\fixtures\q4_plate_meta.csv
rdml,data\raw\stepone_std.rdml,outputs\batch_run_002,25,96,false,
```

Demo workflow:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_public_demo.ps1 -Fixture stepone_std.rdml -PlateSchema 96
```

## Outputs

Each run writes:

- `well_calls.csv`
- `rerun_manifest.csv`
- `plate_qc_summary.json`
- `run_metadata.json`
- `summary.json`
- `report.html`

`summary.json` provides a compact machine-readable rollup for workflow orchestration.

`run_metadata.json` includes execution mode, input hashes, validation summary, structured warning entries, warning codes, per-stage timings, measured runtime in seconds, and peak traced memory in MB.

The HTML report now includes a "Top Flagged Wells" section so reviewers can see the highest-priority non-pass calls without opening CSV artifacts first.

Schema expectations are documented in `docs/io_contract.md` and enforced in `tests/contract/test_output_contract.py`.

When `--plate-meta-csv` is supplied, metadata well IDs are normalized to the same canonical form used by curve rows so control annotations and replicate groups still join correctly.

## Performance

- Current automated runtime coverage includes a synthetic 96-well benchmark fixture in `tests/integration/test_runtime_benchmark.py`
- Full local test suite currently runs in under two seconds on the development machine
- Public RDML spot benchmarks currently include:
  - `stepone_std.rdml` (`960` rows, about `0.06s`)
  - `BioRad_qPCR_melt.rdml` (`2460` rows, about `0.13s`)
  - `lc96_bACTXY.rdml` (`19200` rows, about `1.23s`)
- Larger 96/384-well claims should still be treated as provisional until benchmark evidence is expanded across more machines and fixture types

## Quality Checks

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\deep_sweep.ps1
```

## Validation and Benchmarks

- Benchmark summary: `RESULTS.md`
- Validation protocol and limits: `VALIDATION.md`
- Data provenance snapshot: `docs/data_sources.md`
- Public fixture sources are drawn from the official `PCRuniversum/RDML` example set documented in `docs/data_sources.md`
- Output compatibility is guarded by versioned contract tests in `tests/contract/`

## Public Fixture Coverage

| Fixture | Source family | What it currently proves |
|---|---|---|
| `stepone_std.rdml` | `PCRuniversum/RDML` | ZIP-container RDML parsing, end-to-end pipeline execution, small public benchmark |
| `BioRad_qPCR_melt.rdml` | `PCRuniversum/RDML` | Bio-Rad-style archived RDML parsing, per-cycle temperature capture, medium public benchmark |
| `lc96_bACTXY.rdml` | `PCRuniversum/RDML` | Larger public workload (`19200` rows), numeric react-to-well mapping, larger runtime stress test |

Additional local validation reference:

- `PCRedux_1.2-1.tar.gz` can be kept outside version control and contains public decision files such as `decision_res_stepone_std.csv` and `decision_res_lc96_bACTXY.csv`.
- Those PCRedux decision files strengthen the portfolio story around public reference material, but they are not yet consumed automatically by this Python pipeline.
- A local comparison utility is now available for the cleanest supported fixture mapping:

```powershell
python scripts\compare_pcrredux.py --well-calls outputs\demo_stepone_std\well_calls.csv --fixture stepone_std --pcrredux-tarball data\raw\PCRedux_1.2-1.tar.gz --out outputs\demo_stepone_std\pcrredux_compare.json
```

## Current Limits

- Validation evidence is still based on synthetic fixtures and small public RDML samples
- RDML parsing covers common fixture patterns and aliases, not every vendor-specific export edge case
- The report is intentionally static and lightweight rather than interactive
- The QC layer is deterministic and explainable, but not statistically calibrated against external truth datasets
- Plate geometry is still inferred from the current implementation rather than configured explicitly

## License

MIT. See `LICENSE`.
