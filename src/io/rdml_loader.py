"""RDML ingest helpers for fixture-backed gate checks."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _find_first(node: ET.Element, local_name: str) -> ET.Element | None:
    for child in node.iter():
        if _local_name(child.tag) == local_name:
            return child
    return None


def _extract_value(node: ET.Element, *candidates: str) -> str:
    for key in candidates:
        if key in node.attrib and str(node.attrib[key]).strip():
            return str(node.attrib[key]).strip()
    for candidate in node:
        if _local_name(candidate.tag) in candidates and (candidate.text or "").strip():
            return (candidate.text or "").strip()
    return ""


def _find_plate_id(root: ET.Element, fallback: str) -> str:
    plate = _find_first(root, "plate")
    if plate is None:
        return fallback
    return _extract_value(plate, "id", "name") or fallback


def _find_react_well_id(react: ET.Element) -> str:
    direct = str(react.attrib.get("id", "")).strip().upper()
    if direct:
        return direct
    position_node = _find_first(react, "well")
    if position_node is None:
        position_node = _find_first(react, "position")
    if position_node is None:
        return ""
    return (_extract_value(position_node, "id", "well") or (position_node.text or "")).strip().upper()


def extract_rdml_metadata(path: str | Path) -> dict:
    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"RDML XML parse error in {source}: {exc}") from exc

    run = _find_first(root, "run")
    run_id = run.attrib.get("id", "") if run is not None else ""
    if not run_id:
        run_id = source.stem

    instrument_node = _find_first(root, "instrument")
    instrument = "unknown_instrument"
    if instrument_node is not None:
        instrument = _extract_value(instrument_node, "id", "name", "model") or instrument

    plate_id = _find_plate_id(root, fallback=run_id)

    return {"run_id": run_id, "instrument": instrument, "plate_id": plate_id}


def load_rdml(path: str | Path) -> list[dict]:
    rows, _ = load_rdml_with_report(path)
    return rows


def load_rdml_with_report(path: str | Path) -> tuple[list[dict], dict]:
    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"RDML XML parse error in {source}: {exc}") from exc

    metadata = extract_rdml_metadata(source)
    rows: list[dict] = []
    malformed_reason_counts: dict[str, int] = {"missing_fields": 0, "type_cast_error": 0}
    total_data_nodes = 0

    for react in root.iter():
        if _local_name(react.tag) != "react":
            continue
        well_id = _find_react_well_id(react)
        if not well_id:
            continue

        sample_node = _find_first(react, "sample")
        sample_id = (
            _extract_value(sample_node, "id", "name", "sample")
            if sample_node is not None
            else "unknown_sample"
        ) or "unknown_sample"

        target_node = _find_first(react, "dye")
        if target_node is None:
            target_node = _find_first(react, "target")
        target_id = (
            _extract_value(target_node, "id", "name", "dye", "target")
            if target_node is not None
            else "unknown_target"
        ) or "unknown_target"

        for data_node in react.iter():
            if _local_name(data_node.tag) != "data":
                continue
            total_data_nodes += 1
            # RDML exports can vary by vendor, so common attribute aliases are accepted.
            cycle_value = _extract_value(data_node, "cyc", "cycle", "cycNr")
            fluor_value = _extract_value(data_node, "fluor", "fluorescence", "fluo")
            if not cycle_value or not fluor_value:
                malformed_reason_counts["missing_fields"] += 1
                continue
            try:
                cycle = int(cycle_value)
                fluorescence = float(fluor_value)
            except ValueError:
                malformed_reason_counts["type_cast_error"] += 1
                continue
            rows.append(
                {
                    "run_id": metadata["run_id"],
                    "plate_id": metadata["plate_id"],
                    "well_id": well_id,
                    "sample_id": sample_id,
                    "target_id": target_id,
                    "cycle": cycle,
                    "fluorescence": fluorescence,
                    "instrument": metadata["instrument"],
                }
            )

    if not rows:
        raise ValueError(f"RDML did not contain any readable react/data rows: {source}")
    malformed_rows = malformed_reason_counts["missing_fields"] + malformed_reason_counts["type_cast_error"]
    report = {
        "file_name": source.name,
        "run_id": metadata["run_id"],
        "plate_id": metadata["plate_id"],
        "instrument": metadata["instrument"],
        "total_data_nodes": total_data_nodes,
        "parsed_rows": len(rows),
        "malformed_rows": malformed_rows,
        "malformed_reason_counts": malformed_reason_counts,
    }
    return rows, report
