# qpcr-quality-control

`qpcr-quality-control` is a deterministic local quality-control pipeline for qPCR amplification curves.
It ingests RDML or canonical curve CSV, performs fast forward-only Viterbi state decoding, applies
lightweight QC rules, and emits auditable CSV/JSON/HTML outputs without requiring hosted services.

The project is positioned as an explainable, reproducible portfolio-grade pipeline prototype rather
than a clinically validated production system.

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

## Outputs

Each run writes:

- `well_calls.csv`
- `rerun_manifest.csv`
- `plate_qc_summary.json`
- `run_metadata.json`
- `report.html`

`run_metadata.json` includes execution mode, input hashes, validation summary, warning list, measured runtime in seconds, and peak traced memory in MB.

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

## Current Limits

- Validation evidence is still based on synthetic fixtures and small public RDML samples
- RDML parsing covers common fixture patterns and aliases, not every vendor-specific export edge case
- The report is intentionally static and lightweight rather than interactive
- The QC layer is deterministic and explainable, but not statistically calibrated against external truth datasets
- Plate geometry is still inferred from the current implementation rather than configured explicitly

## License

MIT. See `LICENSE`.
