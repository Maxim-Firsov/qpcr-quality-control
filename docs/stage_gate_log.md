# Stage Gate Log

Record one entry per gate decision.

## Template

Date (UTC): `YYYY-MM-DDTHH:MM:SSZ`
Gate: `Q#`
Decision: `PASS|FAIL`
Evidence paths:
- `path/to/artifact1`
- `path/to/artifact2`
Summary:
- brief factual result
If FAIL, corrective action:
- exact next steps

---

Date (UTC): `2026-03-06T00:00:00Z`
Gate: `Q0`
Decision: `PASS`
Evidence paths:
- `AGENTS.md`
- `docs/BUILD_TO_FINISH.md`
- `scripts/deep_sweep.ps1`
- `.github/workflows/ci.yml`
Summary:
- Added governance, test enforcement, reproducibility checks, CI, and local git hook integration required to execute "build qpcr-hmm-qc to finish" in a new conversation.

---

Date (UTC): `2026-03-06T07:22:05Z`
Gate: `Q1`
Decision: `PASS`
Evidence paths:
- `data/raw/manifest.csv`
- `docs/data_sources.md`
- `outputs/q1/xml_parse_report.json`
- `tests/unit/test_rdml_loader.py`
Summary:
- Added three manifest-tracked RDML fixtures with distinct source URLs and instrument tags, implemented deterministic RDML XML intake parsing, and generated a parse report with zero fatal errors and no hash mismatches.

---

Date (UTC): `2026-03-06T07:27:36Z`
Gate: `Q2`
Decision: `PASS`
Evidence paths:
- `src/io/rdml_loader.py`
- `docs/io_contract.md`
- `tests/unit/test_csv_loader.py`
- `tests/unit/test_normalize.py`
- `tests/unit/test_validate.py`
- `tests/unit/test_canonicalization_contract.py`
- `outputs/q2/canonicalization_report.json`
Summary:
- Locked parser path from RDML to canonical schema, added schema-level canonicalization tests, and generated a canonicalization report showing all non-excluded fixtures mapped with zero schema failures and explicit malformed-row counts.

---

Date (UTC): `2026-03-06T07:30:19Z`
Gate: `Q3`
Decision: `PASS`
Evidence paths:
- `config/model_v1.yaml`
- `src/core/hmm_infer.py`
- `tests/unit/test_hmm_infer.py`
- `outputs/q3/runtime_benchmark.json`
Summary:
- Locked inference thresholds to `model_v1`, added deterministic-model unit coverage, and produced benchmark evidence confirming state-path emission for all eligible curves, repeat-run determinism, and runtime target compliance.

---

Date (UTC): `2026-03-06T07:32:54Z`
Gate: `Q4`
Decision: `PASS`
Evidence paths:
- `src/core/qc_rules.py`
- `tests/unit/test_qc_rules.py`
- `outputs/q4/well_calls.csv`
- `outputs/q4/rerun_manifest.csv`
- `outputs/q4/q4_check_report.json`
Summary:
- Added replicate discordance and rerun decision logic, generated full fixture plate outputs, and confirmed three synthetic failure cases with explicit rerun reasons in manifest output.

---

Date (UTC): `2026-03-06T07:35:39Z`
Gate: `Q5`
Decision: `PASS`
Evidence paths:
- `src/report/render.py`
- `tests/contract/test_output_contract.py`
- `outputs/q5/plate_qc_summary.json`
- `outputs/q5/report.html`
- `outputs/q5/run_metadata.json`
- `outputs/q5/contract_test_report.json`
Summary:
- Extended report sections to include overview/per-plate/rerun rationale, added metadata input hash fields, enforced contract checks, and generated Q5 contract evidence with all checks passing.

---

Date (UTC): `2026-03-06T07:38:30Z`
Gate: `Q6`
Decision: `PASS`
Evidence paths:
- `RESULTS.md`
- `VALIDATION.md`
- `tests/integration/test_pipeline_cli.py`
- `outputs/q6/reproducibility_report.json`
Summary:
- Added benchmark and validation documentation with evidence-backed metrics, produced deterministic repeat-run hash evidence, and verified integration + contract + full suite checks required for release-candidate readiness.
