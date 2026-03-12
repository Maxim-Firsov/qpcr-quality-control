"""RDML ingest helpers for fixture-backed gate checks."""

from __future__ import annotations

import zipfile
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


def _find_direct_child(node: ET.Element, local_name: str) -> ET.Element | None:
    for child in list(node):
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


def _load_rdml_root(path: str | Path) -> ET.Element:
    source = Path(path)
    try:
        return ET.parse(source).getroot()
    except ET.ParseError:
        if source.suffix.lower() != ".rdml":
            raise
        try:
            with zipfile.ZipFile(source) as archive:
                xml_candidates = [name for name in archive.namelist() if name.lower().endswith(".xml")]
                preferred = [name for name in xml_candidates if name.lower() in {"rdml_data.xml", f"{source.stem.lower()}.xml"}]
                members = preferred or xml_candidates
                if not members:
                    raise ValueError(f"RDML archive did not contain an XML payload: {source}")
                return ET.fromstring(archive.read(members[0]))
        except zipfile.BadZipFile as exc:
            raise ValueError(f"RDML XML parse error in {source}: {exc}") from exc
        except ET.ParseError as exc:
            raise ValueError(f"RDML XML parse error in {source}: {exc}") from exc


def _find_plate_id(root: ET.Element, fallback: str) -> str:
    plate = _find_first(root, "plate")
    if plate is None:
        return fallback
    return _extract_value(plate, "id", "name") or fallback


def _pcr_format_shape(root: ET.Element) -> tuple[int, int] | None:
    node = _find_first(root, "pcrFormat")
    if node is None:
        return None
    rows_node = _find_direct_child(node, "rows")
    cols_node = _find_direct_child(node, "columns")
    if rows_node is not None and cols_node is not None:
        try:
            return (int((rows_node.text or "").strip()), int((cols_node.text or "").strip()))
        except ValueError:
            pass
    text = ((node.text or "")).strip().lower()
    if text in {"96", "96-well"}:
        return (8, 12)
    if text in {"384", "384-well"}:
        return (16, 24)
    return None


def _numeric_well_to_alphanumeric(raw_well_id: str, plate_shape: tuple[int, int] | None) -> str:
    if not plate_shape or not raw_well_id.isdigit():
        return raw_well_id
    index = int(raw_well_id)
    if index <= 0:
        return raw_well_id
    row_count, col_count = plate_shape
    zero_based = index - 1
    row_index = zero_based // col_count
    col_index = (zero_based % col_count) + 1
    if row_index >= row_count:
        return raw_well_id
    row_label = chr(ord("A") + row_index)
    return f"{row_label}{col_index:02d}"


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
        root = _load_rdml_root(source)
    except ValueError as exc:
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
        root = _load_rdml_root(source)
    except ValueError as exc:
        raise ValueError(f"RDML XML parse error in {source}: {exc}") from exc

    metadata = extract_rdml_metadata(source)
    plate_shape = _pcr_format_shape(root)
    rows: list[dict] = []
    malformed_reason_counts: dict[str, int] = {"missing_fields": 0, "type_cast_error": 0}
    total_data_nodes = 0

    for react in root.iter():
        if _local_name(react.tag) != "react":
            continue
        well_id = _numeric_well_to_alphanumeric(_find_react_well_id(react), plate_shape)
        if not well_id:
            continue

        sample_node = _find_direct_child(react, "sample")
        sample_id = (
            _extract_value(sample_node, "id", "name", "sample")
            if sample_node is not None
            else "unknown_sample"
        ) or "unknown_sample"

        data_nodes = [child for child in list(react) if _local_name(child.tag) == "data"]
        if not data_nodes:
            continue

        for data_node in data_nodes:
            total_data_nodes += 1
            target_node = _find_direct_child(data_node, "tar")
            if target_node is None:
                target_node = _find_direct_child(data_node, "dye")
            if target_node is None:
                target_node = _find_direct_child(react, "target")
            target_id = (
                _extract_value(target_node, "id", "name", "dye", "target", "tar")
                if target_node is not None
                else "unknown_target"
            ) or "unknown_target"

            adp_nodes = [child for child in list(data_node) if _local_name(child.tag) == "adp"]
            if adp_nodes:
                for adp in adp_nodes:
                    cycle_value = _extract_value(adp, "cyc", "cycle", "cycNr")
                    fluor_value = _extract_value(adp, "fluor", "fluorescence", "fluo")
                    if not cycle_value or not fluor_value:
                        malformed_reason_counts["missing_fields"] += 1
                        continue
                    try:
                        cycle = int(float(cycle_value))
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
                continue

            # RDML exports can vary by vendor, so common attribute aliases are accepted.
            cycle_value = _extract_value(data_node, "cyc", "cycle", "cycNr")
            fluor_value = _extract_value(data_node, "fluor", "fluorescence", "fluo")
            if not cycle_value or not fluor_value:
                malformed_reason_counts["missing_fields"] += 1
                continue
            try:
                cycle = int(float(cycle_value))
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
