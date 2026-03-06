import json

from src.export.writers import write_csv, write_json


def test_writers_emit_files(tmp_path):
    csv_path = tmp_path / "x" / "out.csv"
    json_path = tmp_path / "x" / "out.json"
    write_csv(csv_path, [{"a": 1}], ["a"])
    write_json(json_path, {"ok": True})
    assert csv_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["ok"] is True
