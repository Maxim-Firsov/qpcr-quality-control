# Data Sources

Snapshot date: 2026-03-05

Q1 fixture provenance snapshot (2026-03-06 UTC):

- `rdml_abi_7500.rdml`
  - source URL: `https://example.org/rdml/abi-7500-demo`
  - instrument tag: `ABI_7500`
  - note: deterministic synthetic fixture for parser and intake checks
- `rdml_biorad_cfx96.rdml`
  - source URL: `https://example.org/rdml/biorad-cfx96-demo`
  - instrument tag: `BioRad_CFX96`
  - note: deterministic synthetic fixture for parser and intake checks
- `rdml_roche_lc480.rdml`
  - source URL: `https://example.org/rdml/roche-lc480-demo`
  - instrument tag: `Roche_LightCycler_480`
  - note: deterministic synthetic fixture for parser and intake checks

Each fixture hash and acquisition timestamp is tracked in `data/raw/manifest.csv`.
