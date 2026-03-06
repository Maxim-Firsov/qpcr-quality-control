"""Minimal HTML report renderer."""

from __future__ import annotations


def render_report(summary: dict) -> str:
    plate_rows = []
    for plate in summary.get("plates", []):
        plate_rows.append(
            "<tr>"
            f"<td>{plate['plate_id']}</td>"
            f"<td>{plate['well_total']}</td>"
            f"<td>{plate['pass_count']}</td>"
            f"<td>{plate['review_count']}</td>"
            f"<td>{plate['rerun_count']}</td>"
            f"<td>{plate['plate_status']}</td>"
            "</tr>"
        )
    rows = "".join(plate_rows)
    return (
        "<html><head><title>qPCR HMM QC Report</title></head><body>"
        "<h1>qPCR HMM QC Summary</h1>"
        "<table border='1'>"
        "<tr><th>Plate</th><th>Total</th><th>Pass</th><th>Review</th><th>Rerun</th><th>Status</th></tr>"
        f"{rows}</table></body></html>"
    )
