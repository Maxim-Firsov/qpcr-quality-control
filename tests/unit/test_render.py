from src.report.render import render_report


def test_render_report_has_table():
    html = render_report(
        {
            "generated_at_utc": "2026-03-12T00:00:00Z",
            "global_counts": {"pass": 90, "review": 4, "rerun": 2},
            "plates": [
                {
                    "plate_id": "p1",
                    "well_total": 96,
                    "pass_count": 90,
                    "review_count": 4,
                    "rerun_count": 2,
                    "ntc_contamination_count": 1,
                    "replicate_discordance_count": 1,
                    "edge_effect_alert": True,
                    "plate_status": "review",
                }
            ]
        }
    )
    assert "<table" in html
    assert "p1" in html
    assert "Overview" in html
    assert "Per-Plate Summary" in html
    assert "Plate Alerts" in html
    assert "Rerun Rationale" in html
    assert "Generated at 2026-03-12T00:00:00Z" in html
