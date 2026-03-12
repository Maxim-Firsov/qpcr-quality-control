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


def test_load_rdml_supports_common_alias_fields(tmp_path):
    rdml_file = tmp_path / "alias.rdml"
    rdml_file.write_text(
        """
<rdml>
  <run id="run_alias">
    <instrument><name>AliasMachine</name></instrument>
    <plate id="plate_alias" />
    <react>
      <position><well>C07</well></position>
      <sample><name>sample_alias</name></sample>
      <target><name>TARGET_X</name></target>
      <data><cycNr>1</cycNr><fluo>0.11</fluo></data>
      <data><cycNr>2</cycNr><fluo>0.36</fluo></data>
    </react>
  </run>
</rdml>
""".strip(),
        encoding="utf-8",
    )

    rows = load_rdml(rdml_file)
    metadata = extract_rdml_metadata(rdml_file)

    assert metadata["plate_id"] == "plate_alias"
    assert metadata["instrument"] == "AliasMachine"
    assert rows[0]["well_id"] == "C07"
    assert rows[0]["sample_id"] == "sample_alias"
    assert rows[0]["target_id"] == "TARGET_X"
    assert rows[1]["plate_id"] == "plate_alias"


def test_load_rdml_reads_public_zip_container_fixture():
    rows = load_rdml("data/raw/stepone_std.rdml")
    metadata = extract_rdml_metadata("data/raw/stepone_std.rdml")

    assert len(rows) > 0
    assert metadata["run_id"]
    assert rows[0]["cycle"] >= 1
    assert rows[0]["well_id"]


def test_load_rdml_reads_lc96_public_fixture():
    rows = load_rdml("data/raw/lc96_bACTXY.rdml")
    metadata = extract_rdml_metadata("data/raw/lc96_bACTXY.rdml")

    assert len(rows) == 19200
    assert rows[0]["well_id"].startswith("A")
    assert metadata["run_id"]


def test_load_rdml_reads_biorad_public_fixture():
    rows = load_rdml("data/raw/BioRad_qPCR_melt.rdml")
    metadata = extract_rdml_metadata("data/raw/BioRad_qPCR_melt.rdml")

    assert len(rows) == 2460
    assert rows[0]["well_id"].startswith("A")
    assert metadata["run_id"]
