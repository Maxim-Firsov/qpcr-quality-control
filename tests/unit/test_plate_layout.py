from src.core.plate_layout import is_edge_well, resolve_plate_shape


def test_resolve_plate_shape_defaults_to_standard_geometry():
    assert resolve_plate_shape(["A01", "H12"], plate_schema="auto") == (8, 12)
    assert resolve_plate_shape(["A01", "P24"], plate_schema="auto") == (16, 24)


def test_is_edge_well_uses_plate_shape_boundaries():
    assert is_edge_well("A01", (8, 12)) is True
    assert is_edge_well("H12", (8, 12)) is True
    assert is_edge_well("H12", (16, 24)) is False
    assert is_edge_well("P24", (16, 24)) is True
