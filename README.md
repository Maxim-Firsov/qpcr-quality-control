# qpcr-quality-control

[![CI](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Maxim-Firsov/qpcr-quality-control/actions/workflows/ci.yml)

Deterministic qPCR quality control for local workflows.

`qpcr-quality-control` ingests RDML or canonical curve CSV input, performs sequence-aware amplification state decoding, applies configurable QC rules, and writes auditable CSV, JSON, and HTML outputs.

## Highlights

- RDML support for both plain XML and ZIP-container `.rdml` files
- Canonical CSV mode for testing, adapters, and fixture-driven workflows
- Deterministic forward-only Viterbi decoding
- Ct estimation from adjusted amplification curves
- QC rules for NTC contamination, replicate discordance, positive-control failure, late amplification, low-signal curves, and edge-effect review
- Geometry-aware plate handling for `96`, `384`, or `auto`
- Machine-readable `summary.json` and detailed `run_metadata.json`
- Batch manifest mode for multi-run processing
- Policy-driven non-zero exits for workflow gating
- Public RDML fixture coverage and automated CI

## Quick Start

Run the public demo fixture:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_public_demo.ps1 -Fixture stepone_std.rdml -PlateSchema 96
```

Main review artifacts:

- `outputs/demo_stepone_std/summary.json`
- `outputs/demo_stepone_std/report.html`
- `outputs/demo_stepone_std/well_calls.csv`

If `data\raw\PCRedux_1.2-1.tar.gz` is present locally, the demo also writes:

- `outputs/demo_stepone_std/pcrredux_compare.json`

## Installation

```powershell
python -m pip install -e .
```

## Usage

RDML input:

```powershell
python -m src.cli --rdml data\raw --outdir outputs\run_rdml --min-cycles 25 --plate-schema auto
```

Canonical CSV input:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --plate-meta-csv data\fixtures\q4_plate_meta.csv --outdir outputs\run_csv --min-cycles 3 --plate-schema 96
```

Threshold overrides:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\tuned_run --min-cycles 25 --plate-schema 96 --confidence-threshold 0.7 --late-ct-threshold 33 --low-signal-threshold 0.2
```

Normalization profile override:

```powershell
python -m src.cli --rdml data\raw\stepone_std.rdml --outdir outputs\normalized_run --plate-schema 96 --normalization-profile roche_lc480_standard
```

Batch manifest mode:

```powershell
python -m src.cli --batch-manifest batch_runs.csv --outdir outputs\batch
```

Example batch manifest:

```csv
input_mode,input_path,outdir,min_cycles,plate_schema,allow_empty_run,plate_meta_csv
curve_csv,data\fixtures\q4_curves.csv,outputs\batch_run_001,3,96,false,data\fixtures\q4_plate_meta.csv
rdml,data\raw\stepone_std.rdml,outputs\batch_run_002,25,96,false,
```

Workflow gating:

```powershell
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-review
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-rerun
python -m src.cli --curve-csv data\fixtures\q4_curves.csv --outdir outputs\gate_run --min-cycles 3 --fail-on-edge-alert
```

By default the CLI exits non-zero if validation rejects every well-target curve. Use `--allow-empty-run` only when an upstream workflow explicitly wants empty audited outputs.

## Outputs

Each run writes:

- `well_calls.csv`
- `rerun_manifest.csv`
- `plate_qc_summary.json`
- `run_metadata.json`
- `summary.json`
- `report.html`

`summary.json` is the fastest artifact to consume in automation.

`run_metadata.json` includes:

- input hashes
- validation counts
- structured warnings and warning codes
- QC thresholds used for the run
- normalization config path and hash
- per-stage timings
- total runtime
- peak traced memory

The HTML report includes plate summaries, alerts, rerun rationale, and top flagged wells.

## Public Fixture Coverage

| Fixture | What it demonstrates |
|---|---|
| `stepone_std.rdml` | ZIP-container RDML parsing, end-to-end execution, small public benchmark |
| `BioRad_qPCR_melt.rdml` | archived RDML parsing, per-cycle temperature capture, medium public benchmark |
| `lc96_bACTXY.rdml` | larger public workload, numeric react-to-well mapping, larger runtime stress test |

Optional local reference material:

- `data\raw\PCRedux_1.2-1.tar.gz`

Supported comparison command:

```powershell
python scripts\compare_pcrredux.py --well-calls outputs\demo_stepone_std\well_calls.csv --fixture stepone_std --pcrredux-tarball data\raw\PCRedux_1.2-1.tar.gz --out outputs\demo_stepone_std\pcrredux_compare.json
```

## Performance

Current public spot benchmarks on the development machine:

- `stepone_std.rdml`: `960` rows in about `0.06s`
- `BioRad_qPCR_melt.rdml`: `2460` rows in about `0.13s`
- `lc96_bACTXY.rdml`: `19200` rows in about `1.23s`

The full local test suite currently runs in about three seconds.

## Validation and Compatibility

- Benchmark details: `RESULTS.md`
- Validation notes and limits: `VALIDATION.md`
- Data provenance: `docs/data_sources.md`
- I/O contract: `docs/io_contract.md`
- Contract and compatibility checks: `tests/contract/`

## Repository Layout

- `src/` implementation
- `tests/` unit, integration, and contract tests
- `data/raw/` RDML fixtures and provenance manifest
- `data/fixtures/` synthetic validation fixtures
- `docs/` architecture, contracts, and source notes
- `scripts/` demo, comparison, and validation utilities

## Notes

- Designed for local execution
- Deterministic outputs are favored over opaque model behavior
- Public-fixture coverage improves parser and throughput confidence, but does not substitute for assay-specific validation
- Assay- and instrument-aware normalization profiles are deterministic config, not biological calibration

## License

MIT. See `LICENSE`.
