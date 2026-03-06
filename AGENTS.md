# AGENTS.md - `qpcr-hmm-qc`

This file is the authoritative execution contract for Codex agents working in this repository.

## Mission Scope

- Deliver `qpcr-hmm-qc` to `v0.1.0` completion under the stage gates in `docs/BUILD_TO_FINISH.md`.
- Prioritize deterministic behavior, auditability, and lab-operational QC utility.
- Reject work outside current gate unless explicitly requested by the owner.

## Mandatory Build Rules

- Follow gate order strictly: `Q1 -> Q2 -> Q3 -> Q4 -> Q5 -> Q6`.
- Add or update unit tests for every touched pipeline step in the same change.
- Add a regression test for every new bug/edge case before closing the issue.
- Run targeted tests, then full test suite, then end-to-end pipeline check.
- Run a deep sweep (`scripts/deep_sweep.ps1`) before commit.
- Commit only when all required checks pass.
- Push immediately after successful scoped action set.

## Hallucination Prevention Rules

- Do not claim dataset facts, model metrics, or benchmark values without artifact evidence.
- Do not mark a stage gate complete without all required files present.
- Treat docs as contracts: code and docs must be aligned in same PR/commit.
- If uncertain, record uncertainty in stage log and create an evidence task.

## Git and Quality Gate Rules

- Use `scripts/pre_push_check.ps1` before each push.
- Keep commits scoped and descriptive; include test evidence summary in commit body when logic changes.
- Never delete unrelated files or revert user-owned unrelated changes.

## Required Operational Artifacts

- `docs/stage_gate_log.md` must be updated for each gate decision.
- `outputs/q*/` evidence artifacts must be written for corresponding gate runs.
- `RESULTS.md` and `VALIDATION.md` must be updated at `Q6`.
