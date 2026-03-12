"""Minimal HTML report renderer."""

from __future__ import annotations


def render_report(summary: dict) -> str:
    plate_rows = []
    rerun_items = []
    alert_items = []
    global_counts = summary.get("global_counts", {})
    for plate in summary.get("plates", []):
        plate_rows.append(
            "<tr>"
            f"<td>{plate['plate_id']}</td>"
            f"<td>{plate['well_total']}</td>"
            f"<td>{plate['pass_count']}</td>"
            f"<td>{plate['review_count']}</td>"
            f"<td>{plate['rerun_count']}</td>"
            f"<td>{'yes' if plate.get('edge_effect_alert') else 'no'}</td>"
            f"<td>{plate['plate_status']}</td>"
            "</tr>"
        )
        if int(plate.get("rerun_count", 0)) > 0:
            rerun_items.append(
                "<li>"
                f"{plate['plate_id']}: rerun_count={plate['rerun_count']}, "
                f"ntc_contamination_count={plate.get('ntc_contamination_count', 0)}, "
                f"replicate_discordance_count={plate.get('replicate_discordance_count', 0)}"
                "</li>"
            )
        if plate.get("edge_effect_alert"):
            alert_items.append(f"<li>{plate['plate_id']}: edge-well failures exceed inner-well failures.</li>")
    rows = "".join(plate_rows)
    rerun_html = "<ul>" + "".join(rerun_items) + "</ul>" if rerun_items else "<p>No rerun-triggering flags detected.</p>"
    alert_html = "<ul>" + "".join(alert_items) + "</ul>" if alert_items else "<p>No plate-level alerts triggered.</p>"
    generated_at = summary.get("generated_at_utc", "unknown")
    return (
        "<html><head><title>qPCR Quality Control Report</title>"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#16202a;}"
        ".cards{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 20px;}"
        ".card{border:1px solid #c8d2dc;border-radius:8px;padding:12px 16px;min-width:120px;background:#f7fafc;}"
        "table{border-collapse:collapse;width:100%;margin-top:8px;}"
        "th,td{border:1px solid #c8d2dc;padding:8px;text-align:left;}"
        "th{background:#edf3f8;}"
        "</style></head><body>"
        "<h1>qPCR Quality Control Summary</h1>"
        f"<p>Generated at {generated_at}</p>"
        "<h2>Overview</h2>"
        "<div class='cards'>"
        f"<div class='card'><strong>Pass</strong><div>{global_counts.get('pass', 0)}</div></div>"
        f"<div class='card'><strong>Review</strong><div>{global_counts.get('review', 0)}</div></div>"
        f"<div class='card'><strong>Rerun</strong><div>{global_counts.get('rerun', 0)}</div></div>"
        "</div>"
        "<h2>Per-Plate Summary</h2>"
        "<table>"
        "<tr><th>Plate</th><th>Total</th><th>Pass</th><th>Review</th><th>Rerun</th><th>Edge Alert</th><th>Status</th></tr>"
        f"{rows}</table>"
        "<h2>Plate Alerts</h2>"
        f"{alert_html}"
        "<h2>Rerun Rationale</h2>"
        f"{rerun_html}</body></html>"
    )
