# Architecture

Pipeline flow:

1. `io/csv_loader.py` loads canonical curve rows.
2. `core/normalize.py` standardizes identifiers and types.
3. `core/validate.py` applies schema and per-well constraints.
4. `core/features.py` computes deterministic transform features.
5. `core/hmm_infer.py` infers state paths (deterministic scaffold).
6. `core/qc_rules.py` applies QC decisions and flags.
7. `core/aggregate.py` computes plate-level status summary.
8. `export/writers.py` serializes CSV/JSON artifacts.
9. `report/render.py` writes minimal HTML report.
