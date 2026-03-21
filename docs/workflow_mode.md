# Workflow Mode

## Operational Split

`qpcr-quality-control` uses two layers on purpose:

- the CLI is the per-run analysis engine
- Snakemake is the batch operations layer

The CLI owns ingestion, normalization, feature extraction, deterministic state calling, QC decisions, and per-run serialization. The workflow layer owns manifest preflight, stable run directories, resumability, selective artifact generation, batch aggregation, rerun consolidation, and release gating.

## Why This Matters In Practice

Real lab review rarely happens as one isolated run. Teams typically need to process a manifest of runs, resume after interruptions, avoid generating heavyweight HTML for every passing plate, consolidate rerun candidates, and hand off a single batch packet to the next reviewer or queue.

That is why Snakemake is necessary here. It adds orchestration and recovery semantics that do not belong inside the analysis engine itself.

## Default Batch Behavior

The workflow default is `artifact_profile=review`.

That means:

- every run gets compact machine-readable outputs
- passing runs avoid unnecessary `report.html` and `well_calls.csv`
- review or rerun runs keep richer reviewer-facing artifacts
- aggregation always reads machine-readable outputs and never depends on `report.html`

## Batch Packet

The canonical batch deliverable is:

- `batch_master.json`

Spreadsheet-friendly companion:

- `batch_master.tsv`

Additional handoff artifacts:

- `rerun_queue.csv`
- `failure_reason_counts.tsv`
- `batch_gate_status.json`
- `batch_report.md`

## Command

```powershell
python -m snakemake --snakefile Snakefile --cores 1 --configfile workflow\config\batch_config.yaml
```

## Manifest Notes

Manifest rows are TSV records with stable `run_id` values. Each row maps to one stable run directory under `output_root/runs/<run_id>`, which is what gives the workflow resumability and selective reruns.
