# VALIDATION

Gate completed: `Q6` on 2026-03-06 UTC.

## 1. Dataset Provenance and Snapshot Date

- RDML intake fixtures: `data/raw/*.rdml` tracked in `data/raw/manifest.csv`
- Q4/Q5/Q6 validation fixture: `data/fixtures/q4_curves.csv` with metadata `data/fixtures/q4_plate_meta.csv`
- Snapshot date: 2026-03-06 UTC
- Fixture type: deterministic synthetic validation fixture for gate evidence, not clinical data

## 2. Labeling Methodology

Expected QC outcomes were assigned directly from fixture design intent:

- `A01` (`control_type=ntc`) contains amplification profile and should trigger `ntc_contamination` rerun.
- `A02` and `A03` are replicate group `rg1` with conflicting amplification labels and should trigger `replicate_discordance` rerun.
- `B01` is a clean amplified sample and should pass.

Ground truth was compared against generated `well_calls.csv`/`rerun_manifest.csv` outputs from repeated runs.

## 3. Metrics and Confidence Intervals

Observed on the Q4 synthetic fixture:

- Rerun detection for designed failure wells: `3/3` (100%)
- Overall expected well-level QC status match: `4/4` (100%)

95% Wilson confidence intervals (small-sample, binomial):

- Failure-well rerun detection (`3/3`): `[0.4385, 1.0000]`
- Overall expected status match (`4/4`): `[0.5101, 1.0000]`

Supporting evidence:

- `outputs/q4/q4_check_report.json`
- `outputs/q6/reproducibility_report.json`

## 4. Known Failure Modes and Limitations

- Current validation is synthetic and low-scale; no claim is made about clinical sensitivity/specificity.
- RDML parsing currently targets common minimal structures in fixtures and may require extensions for vendor-specific edge schemas.
- Confidence and state assignment use deterministic threshold logic in `v0.1.0`; statistical calibration against external truth datasets is not included yet.
- Runtime and memory measurements were collected on a small fixture and should be re-benchmarked on full plate datasets before production deployment.
