# Build To Finish - `qpcr-hmm-qc`

Use this file as the executable build plan for the command: `build qpcr-hmm-qc to finish`.

## Global Execution Contract

1. Gates are strict and sequential: `Q1 -> Q2 -> Q3 -> Q4 -> Q5 -> Q6`.
2. A gate is complete only when:
- all required artifacts exist
- all listed checks pass
- a `PASS` entry is appended to `docs/stage_gate_log.md`
3. On any failure:
- stop downstream work
- append `FAIL` entry to stage log with root cause and next corrective action

## Standard Commands

Run from repository root:

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File scripts/deep_sweep.ps1
```

## Q1 Data Intake Freeze

Required:

- `data/raw/manifest.csv` with: `file_name,source_url,acquired_utc,sha256,license_note,status`
- `docs/data_sources.md` snapshot and provenance
- `outputs/q1/xml_parse_report.json`

Checks:

- at least 3 RDML files from distinct sources/instruments
- every row in manifest has sha256
- XML report has zero fatal parse errors for included fixtures

## Q2 Canonicalization Contract Lock

Required:

- parser path to canonical schema
- schema tests
- `docs/io_contract.md`
- `outputs/q2/canonicalization_report.json`

Checks:

- all non-excluded fixtures map to canonical schema
- malformed rows counted and reported
- unit tests for normalize/validate/load pass

## Q3 HMM Baseline Model

Required:

- deterministic inference implementation
- locked `config/model_v1.yaml`
- model unit tests
- `outputs/q3/runtime_benchmark.json`

Checks:

- state path emitted for every eligible well-target curve
- repeated same-input run produces identical state paths
- benchmark meets runtime target for baseline fixture

## Q4 QC Rule Layer

Required:

- NTC contamination checks
- replicate discordance checks
- rerun decision logic
- `outputs/q4/well_calls.csv`
- `outputs/q4/rerun_manifest.csv`

Checks:

- full fixture plate produces both files
- at least 3 synthetic failure cases detected
- each rerun decision has explicit flags/reasons

## Q5 Reporting and Output Contract

Required:

- `plate_qc_summary.json`
- `report.html`
- `run_metadata.json`
- contract tests
- `outputs/q5/contract_test_report.json`

Checks:

- outputs satisfy required schema in `WORKPLAN.md` section 5.4.2
- report includes overview, per-plate summary, and rerun rationale
- metadata includes config/input hash fields

## Q6 Validation and Release Candidate

Required:

- `RESULTS.md` benchmark section with runnable commands
- `VALIDATION.md` dataset/metrics/limitations
- full integration test
- reproducibility evidence in `outputs/q6/`

Checks:

- repeated runs produce schema-valid deterministic artifacts
- CI passes (`lint/static + unit + contract + integration`)
- only then tag `v0.1.0-rc1`
