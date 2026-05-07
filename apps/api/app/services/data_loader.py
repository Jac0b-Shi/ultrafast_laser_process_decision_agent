from __future__ import annotations

import json
import math
import numbers
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.settings import get_settings


PARAMETER_COLUMNS = [
    "pulse_width_fs",
    "repetition_frequency_khz",
    "scan_speed_mm_s",
    "pulse_energy_mj",
    "laser_energy_percent",
    "defocus_amount_mm",
    "marking_count",
    "fill_spacing_um",
    "scan_interval_um",
    "processing_time_s",
    "average_power_w",
    "peak_power_kw",
]

QUALITY_COLUMNS = ["depth_um", "diameter_um", "roughness_um"]

BASE_COLUMNS = ["case_id", "material", "process_type", "source_file", "source_row"]

FILE_SPECS: dict[str, dict[str, Any]] = {
    "4H碳化硅实验数据.xlsx": {
        "material": "4H碳化硅",
        "fields": {
            "experiment_no": "实验编号",
            "scan_speed_mm_s": "扫描速度(mm/s)",
            "repetition_frequency_khz": "重复频率(kHz)",
            "pulse_width_fs": "脉冲宽度(fs)",
            "depth_um": "深度（μm）",
            "roughness_um": "粗糙度(微米)",
        },
    },
    "BF33实验数据.xlsx": {
        "material": "BF33",
        "fields": {
            "experiment_no": "实验序号",
            "repetition_frequency_khz": "重复频率(kHz)",
            "pulse_width_fs": "脉宽",
            "scan_speed_mm_s": "扫描速度(mm/s)",
            "depth_um": "深度μm",
            "roughness_um": "粗糙度μm",
        },
    },
    "微晶玻璃数据集.xlsx": {
        "material": "微晶玻璃",
        "fields": {
            "pulse_width_fs": "pulse mode",
            "repetition_frequency_khz": "repeat frequency",
            "scan_speed_mm_s": "scanning speed",
            "defocus_amount_mm": "defocus amount",
            "scan_interval_um": "scanning interval",
            "processing_time_s": "processing time",
            "depth_um": "depth",
            "roughness_um": "Sa",
        },
    },
    "金刚石实验结果.xlsx": {
        "material": "金刚石",
        "fields": {
            "experiment_no": "序号",
            "pulse_width_fs": "脉冲宽度",
            "repetition_frequency_khz": "重复频率",
            "fill_spacing_um": "填充间距",
            "marking_count": "加工次数",
            "scan_speed_mm_s": "扫描速度",
            "depth_um": "深度/μm",
            "roughness_um": "粗糙度/μm",
        },
    },
    "高温合金数据集.xlsx": {
        "material": "高温合金",
        "fields": {
            "experiment_no": "number",
            "pulse_width_fs": "pulse mode",
            "repetition_frequency_khz": "pulse frequency",
            "laser_energy_percent": "energy",
            "pulse_energy_mj": "Pulse energy(mJ)",
            "defocus_amount_mm": "defocusing amount",
            "marking_count": "marking frequency",
            "average_power_w": "Average Power(W)",
            "depth_um": "depth",
            "diameter_um": "diameter",
            "peak_power_kw": "Peak Power(kW)",
        },
    },
}


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, numbers.Real):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    if "无法" in text or "未测" in text:
        return None
    if "接近0" in text:
        return 0.0

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _clean_raw_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _row_value(row: pd.Series, column: str | None) -> Any:
    if not column or column not in row:
        return None
    return _clean_raw_value(row[column])


def _read_excel_records(path: Path) -> list[dict[str, Any]]:
    spec = FILE_SPECS.get(path.name)
    if spec is None:
        return []

    frame = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    frame = frame.dropna(how="all")
    fields: dict[str, str] = spec["fields"]
    records: list[dict[str, Any]] = []

    for index, row in frame.iterrows():
        raw_record = {
            str(key): _clean_raw_value(value)
            for key, value in row.items()
            if not str(key).startswith("Unnamed")
        }
        if not any(value is not None for value in raw_record.values()):
            continue

        experiment_no = _row_value(row, fields.get("experiment_no"))
        case_id = f"{path.stem}:{experiment_no if experiment_no is not None else index + 2}"
        record: dict[str, Any] = {
            "case_id": case_id,
            "material": spec["material"],
            "process_type": "超快激光微加工",
            "source_file": path.name,
            "source_row": int(index) + 2,
            "raw_record": json.dumps(raw_record, ensure_ascii=False),
        }

        for column in PARAMETER_COLUMNS + QUALITY_COLUMNS:
            record[column] = parse_number(_row_value(row, fields.get(column)))

        records.append(record)

    return records


def _read_feedback_records() -> list[dict[str, Any]]:
    settings = get_settings()
    path = settings.feedback_jsonl
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            task = payload.get("task", {})
            parameters = payload.get("selected_parameters", {})
            quality = payload.get("measured_quality", {})
            record: dict[str, Any] = {
                "case_id": payload.get("feedback_id", f"feedback:{line_no}"),
                "material": task.get("material") or "反馈样本",
                "process_type": "超快激光微加工",
                "source_file": "feedback.jsonl",
                "source_row": line_no,
                "raw_record": json.dumps(payload, ensure_ascii=False),
            }
            for column in PARAMETER_COLUMNS:
                record[column] = parse_number(parameters.get(column))
            for column in QUALITY_COLUMNS:
                record[column] = parse_number(quality.get(column))
            records.append(record)
    return records


def load_dataset() -> pd.DataFrame:
    settings = get_settings()
    records: list[dict[str, Any]] = []
    for path in sorted(settings.raw_data_dir.glob("*.xlsx")):
        records.extend(_read_excel_records(path))
    records.extend(_read_feedback_records())

    columns = BASE_COLUMNS + PARAMETER_COLUMNS + QUALITY_COLUMNS + ["raw_record"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(records, columns=columns)


def dataset_summary() -> dict[str, Any]:
    settings = get_settings()
    frame = load_dataset()
    raw_files = sorted(path.name for path in settings.raw_data_dir.glob("*.xlsx"))
    feedback_samples = int((frame["source_file"] == "feedback.jsonl").sum()) if not frame.empty else 0

    materials: list[dict[str, Any]] = []
    if not frame.empty:
        for material, group in frame.groupby("material", dropna=False):
            materials.append(
                {
                    "material": str(material),
                    "sample_count": int(len(group)),
                    "source_files": sorted(str(item) for item in group["source_file"].dropna().unique()),
                    "parameter_columns": [
                        column for column in PARAMETER_COLUMNS if group[column].notna().any()
                    ],
                    "quality_metrics": [
                        column for column in QUALITY_COLUMNS if group[column].notna().any()
                    ],
                }
            )

    return {
        "total_samples": int(len(frame)),
        "materials": materials,
        "raw_files": raw_files,
        "feedback_samples": feedback_samples,
    }
