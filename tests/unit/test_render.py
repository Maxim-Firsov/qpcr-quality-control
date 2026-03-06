from src.report.render import render_report


def test_render_report_has_table():
    html = render_report(
        {
            "plates": [
                {
                    "plate_id": "p1",
                    "well_total": 96,
                    "pass_count": 90,
                    "review_count": 4,
                    "rerun_count": 2,
                    "plate_status": "review",
                }
            ]
        }
    )
    assert "<table" in html
    assert "p1" in html
