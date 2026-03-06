from src.io.rdml_loader import extract_rdml_metadata, load_rdml


def test_load_rdml_reads_rows_and_metadata():
    rows = load_rdml("data/raw/rdml_abi_7500.rdml")
    metadata = extract_rdml_metadata("data/raw/rdml_abi_7500.rdml")

    assert len(rows) == 3
    assert metadata["run_id"] == "run_abi_7500"
    assert metadata["instrument"] == "ABI_7500"
    assert rows[0]["well_id"] == "A01"
    assert rows[0]["cycle"] == 1


def test_load_rdml_raises_on_malformed_xml(tmp_path):
    bad_file = tmp_path / "bad.rdml"
    bad_file.write_text("<rdml><broken></rdml>", encoding="utf-8")

    try:
        load_rdml(bad_file)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "parse error" in str(exc).lower()
