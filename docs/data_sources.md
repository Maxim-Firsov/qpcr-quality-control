# Data Sources

Snapshot date: 2026-03-12

Synthetic parser-validation fixtures:

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

Public RDML fixtures added for parser and runtime coverage:

- `stepone_std.rdml`
  - source URL: `https://raw.githubusercontent.com/PCRuniversum/RDML/master/inst/extdata/stepone_std.rdml`
  - source family: official `PCRuniversum/RDML` example fixture
  - observed parsed footprint: `960` rows across `24` well-target traces
- `BioRad_qPCR_melt.rdml`
  - source URL: `https://raw.githubusercontent.com/PCRuniversum/RDML/master/inst/extdata/BioRad_qPCR_melt.rdml`
  - source family: official `PCRuniversum/RDML` example fixture
  - observed parsed footprint: `2460` rows across `60` well-target traces
- `lc96_bACTXY.rdml`
  - source URL: `https://raw.githubusercontent.com/PCRuniversum/RDML/master/inst/extdata/lc96_bACTXY.rdml`
  - source family: official `PCRuniversum/RDML` example fixture
  - observed parsed footprint: `19200` rows across `384` well-target traces

Important note:

- These public RDML files are ZIP-container `.rdml` archives, not plain XML files. The loader now supports both plain-XML and ZIP-container RDML payloads.

Each fixture hash and acquisition timestamp is tracked in `data/raw/manifest.csv`.
