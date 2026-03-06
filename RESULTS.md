# RESULTS

Gate completed: `Q6` on 2026-03-06 UTC.

## 1. Benchmark Environment

- OS: Windows 11 (`10.0.26200`)
- Python: `3.13.6`
- CPU: `AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD`
- Evidence source: `outputs/q6/reproducibility_report.json`

## 2. Exact Commands Used

```powershell
python scripts\generate_q6_release_evidence.py
python -m pytest tests/integration --basetemp .pytest_tmp/q6_integration
python -m pytest tests/contract --basetemp .pytest_tmp/q6_contract
```

## 3. Runtime and Memory Table

| Run | Runtime (s) | Peak Memory (MB) |
|---|---:|---:|
| `run_a` | `0.015411` | `0.173458` |
| `run_b` | `0.012854` | `0.166176` |

Deterministic artifact hash match across repeated runs:

- `well_calls.csv`: match
- `rerun_manifest.csv`: match
- `plate_qc_summary.json`: match
- `run_metadata.json`: match
- `report.html`: match

## 4. Fixture Composition and Limits

- Fixture path: `data/fixtures/q4_curves.csv` + `data/fixtures/q4_plate_meta.csv`
- Plate size in benchmark: 4 wells x 3 cycles (12 curve rows)
- Intentional synthetic failure composition:
  - 1 NTC contamination case
  - 2 replicate discordance-linked rerun wells
  - 1 clean sample well
- Limits:
  - Runtime/memory numbers are from a small synthetic fixture and not representative of full 96/384-well production plates.
  - No external instrument-export variability is represented in this benchmark set.
