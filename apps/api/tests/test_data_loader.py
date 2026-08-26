from app.services.data_loader import load_dataset


def test_load_dataset_from_raw_excel() -> None:
    frame = load_dataset()

    assert len(frame) > 0
    assert {"高温合金", "微晶玻璃", "4H碳化硅", "BF33"}.issubset(set(frame["material"]))
    assert frame["depth_um"].notna().any()


def test_load_new_gbk_csv_materials_with_audit_flags() -> None:
    frame = load_dataset()
    expected = {"AlSiC": 120, "CFRP": 128, "SiC": 120, "ZrO2": 120}
    for material, count in expected.items():
        rows = frame[frame["material"] == material]
        assert len(rows) == count
        assert rows["fill_spacing_um"].notna().all()
        assert rows["sq_um"].notna().all()
        assert rows["sz_um"].notna().all()
    cfrp = frame[frame["material"] == "CFRP"]
    assert cfrp["case_id"].nunique() == len(cfrp)
    alsic = frame[frame["material"] == "AlSiC"]
    assert sum("depth_um:negative_audit_only" in flags for flags in alsic["quality_flags"]) == 8
    assert sum(bool(flags) for flags in alsic["quality_flags"]) == 54
