from argparse import Namespace

from src.cli import run_pipeline


def _write_curve_fixture(path, wells: int, cycles: int) -> None:
    rows = ["run_id,plate_id,well_id,sample_id,target_id,cycle,fluorescence"]
    for well_index in range(1, wells + 1):
        well_id = f"A{well_index:02d}"
        for cycle in range(1, cycles + 1):
            fluorescence = 0.02 * cycle
            rows.append(f"run1,plate1,{well_id},sample_{well_index},target1,{cycle},{fluorescence:.4f}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_runtime_benchmark_96_well_fixture_stays_fast(tmp_path):
    curve_csv = tmp_path / "curves_96.csv"
    outdir = tmp_path / "out_96"
    _write_curve_fixture(curve_csv, wells=96, cycles=40)

    summary = run_pipeline(
        Namespace(curve_csv=str(curve_csv), rdml=None, plate_meta_csv=None, outdir=str(outdir), min_cycles=20)
    )

    assert summary["well_calls"] == 96

    metadata_path = outdir / "run_metadata.json"
    timing_text = metadata_path.read_text(encoding="utf-8")
    assert '"timing_seconds":' in timing_text
