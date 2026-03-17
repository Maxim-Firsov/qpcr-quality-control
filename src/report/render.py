"""Minimal HTML report renderer."""

from __future__ import annotations

from collections import defaultdict


def _well_sort_key(well_id: str) -> tuple[str, int]:
    row = well_id[:1]
    try:
        col = int(well_id[1:])
    except ValueError:
        col = 0
    return (row, col)


def _status_color(call: dict) -> str:
    status = call.get("qc_status", "pass")
    if status == "rerun":
        return "#b42318"
    if status == "review":
        return "#f79009"
    confidence = float(call.get("amplification_confidence", 0.0) or 0.0)
    return "#12b76a" if confidence >= 0.8 else "#7f56d9"


def _sparkline(rows: list[dict]) -> str:
    if not rows:
        return ""
    points = []
    max_signal = max(float(row.get("f_adj", 0.0)) for row in rows)
    min_signal = min(float(row.get("f_adj", 0.0)) for row in rows)
    span = max(max_signal - min_signal, 1e-6)
    x_step = 100 / max(1, len(rows) - 1)
    for index, row in enumerate(rows):
        x = round(index * x_step, 2)
        y = round(40 - (((float(row.get("f_adj", 0.0)) - min_signal) / span) * 32), 2)
        points.append(f"{x},{y}")
    return (
        "<svg viewBox='0 0 100 40' class='sparkline' aria-label='Adjusted fluorescence curve'>"
        f"<polyline fill='none' stroke='#0f172a' stroke-width='2' points='{' '.join(points)}' />"
        "</svg>"
    )


def _heatmap_html(plates: list[dict], well_calls: list[dict]) -> str:
    by_plate: dict[str, list[dict]] = defaultdict(list)
    for call in well_calls:
        by_plate[str(call.get("plate_id", ""))].append(call)

    blocks = []
    for plate in plates:
        plate_id = plate["plate_id"]
        cells = []
        for call in sorted(by_plate.get(plate_id, []), key=lambda item: _well_sort_key(str(item.get("well_id", "")))):
            color = _status_color(call)
            cells.append(
                "<div class='heatmap-cell' "
                f"style='background:{color}' title='{call.get('well_id', '')}: {call.get('qc_status', '')}'>"
                f"{call.get('well_id', '')}</div>"
            )
        if not cells:
            cells.append("<div class='heatmap-empty'>No wells available.</div>")
        blocks.append(
            "<section class='heatmap-block'>"
            f"<h3>{plate_id}</h3>"
            "<div class='heatmap-grid'>"
            + "".join(cells)
            + "</div></section>"
        )
    return "".join(blocks) if blocks else "<p>No plate heatmaps available.</p>"


def _drilldown_html(well_calls: list[dict], curve_rows: list[dict]) -> str:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in curve_rows:
        key = (str(row.get("plate_id", "")), str(row.get("well_id", "")), str(row.get("target_id", "")))
        grouped[key].append(row)

    items = []
    flagged_calls = sorted(
        [call for call in well_calls if call.get("qc_status") != "pass"],
        key=lambda item: (item.get("qc_status") != "rerun", item.get("well_id", "")),
    )[:8]
    for call in flagged_calls:
        key = (str(call.get("plate_id", "")), str(call.get("well_id", "")), str(call.get("target_id", "")))
        rows = sorted(grouped.get(key, []), key=lambda item: item.get("cycle", 0))
        state_path = ", ".join(str(row.get("state", "")) for row in rows[:6])
        items.append(
            "<article class='drilldown-card'>"
            f"<h3>{call.get('plate_id', '')} {call.get('well_id', '')} {call.get('target_id', '')}</h3>"
            f"<p>Status: <strong>{call.get('qc_status', '')}</strong> | Flags: {call.get('qc_flags', '')}</p>"
            f"{_sparkline(rows)}"
            f"<p class='microcopy'>Leading states: {state_path or 'n/a'}</p>"
            "</article>"
        )
    return "".join(items) if items else "<p>No flagged curve drilldowns available.</p>"


def render_report(
    summary: dict,
    well_calls: list[dict] | None = None,
    curve_rows: list[dict] | None = None,
) -> str:
    well_calls = well_calls or []
    curve_rows = curve_rows or []
    plate_rows = []
    rerun_items = []
    alert_items = []
    flagged_rows = []
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
    for call in sorted(
        [call for call in well_calls if call.get("qc_status") != "pass"],
        key=lambda item: (item.get("qc_status") != "rerun", item.get("amplification_confidence", 0.0), item.get("well_id", "")),
    )[:10]:
        flagged_rows.append(
            "<tr>"
            f"<td>{call.get('plate_id', '')}</td>"
            f"<td>{call.get('well_id', '')}</td>"
            f"<td>{call.get('target_id', '')}</td>"
            f"<td>{call.get('qc_status', '')}</td>"
            f"<td>{call.get('ct_estimate', '')}</td>"
            f"<td>{call.get('qc_flags', '')}</td>"
            "</tr>"
        )
    flagged_html = (
        "<table><tr><th>Plate</th><th>Well</th><th>Target</th><th>Status</th><th>Ct</th><th>Flags</th></tr>"
        + "".join(flagged_rows)
        + "</table>"
        if flagged_rows
        else "<p>No non-pass wells detected.</p>"
    )
    heatmap_html = _heatmap_html(summary.get("plates", []), well_calls)
    drilldown_html = _drilldown_html(well_calls, curve_rows)
    generated_at = summary.get("generated_at_utc", "unknown")
    return (
        "<html><head><title>qPCR Quality Control Report</title>"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;max-width:1160px;margin:24px auto;padding:0 16px;color:#16202a;background:linear-gradient(180deg,#f8fbff 0%,#ffffff 35%);}"
        ".cards{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 20px;}"
        ".card{border:1px solid #c8d2dc;border-radius:12px;padding:12px 16px;min-width:120px;background:#f7fafc;box-shadow:0 8px 24px rgba(15,23,42,.05);}"
        "table{border-collapse:collapse;width:100%;margin-top:8px;background:#fff;}"
        "th,td{border:1px solid #c8d2dc;padding:8px;text-align:left;}"
        "th{background:#edf3f8;}"
        ".heatmap-block{margin:16px 0 24px;}"
        ".heatmap-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(56px,1fr));gap:6px;}"
        ".heatmap-cell{color:#fff;border-radius:8px;padding:10px 6px;text-align:center;font-size:12px;font-weight:700;}"
        ".heatmap-empty{padding:12px;border:1px dashed #c8d2dc;border-radius:8px;color:#475467;}"
        ".drilldown-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;}"
        ".drilldown-card{border:1px solid #d0d5dd;border-radius:12px;padding:14px;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.05);}"
        ".sparkline{width:100%;height:70px;background:#f8fafc;border-radius:8px;}"
        ".microcopy{color:#475467;font-size:13px;}"
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
        "<h2>Plate Heatmaps</h2>"
        f"{heatmap_html}"
        "<h2>Plate Alerts</h2>"
        f"{alert_html}"
        "<h2>Top Flagged Wells</h2>"
        f"{flagged_html}"
        "<h2>Curve Drilldowns</h2>"
        f"<div class='drilldown-grid'>{drilldown_html}</div>"
        "<h2>Rerun Rationale</h2>"
        f"{rerun_html}</body></html>"
    )
