from app.services.data_loader import load_dataset


def test_load_dataset_from_raw_excel() -> None:
    frame = load_dataset()

    assert len(frame) > 0
    assert {"高温合金", "微晶玻璃", "4H碳化硅", "BF33"}.issubset(set(frame["material"]))
    assert frame["depth_um"].notna().any()
