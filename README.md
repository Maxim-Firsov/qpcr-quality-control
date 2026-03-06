# qpcr-hmm-qc

Deterministic qPCR QC scaffold with HMM-style state inference and auditable outputs.

## Quick Start

```powershell
python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\deep_sweep.ps1
```

Run CSV-mode pipeline:

```powershell
python -m src.cli --curve-csv path\to\curves.csv --outdir outputs\run1 --min-cycles 3
```

## Build Governance

- Agent operating contract: `AGENTS.md`
- End-to-end stage gates: `docs/BUILD_TO_FINISH.md`
- Gate decisions: `docs/stage_gate_log.md`

## Git Quality Integration

Enable local pre-push checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_git_hooks.ps1
```
