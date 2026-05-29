from __future__ import annotations

import json
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.schemas import ExperimentData, MaterialListResponse, ExperimentDataListResponse, MaterialInfo
from app.services.data_loader import load_dataset

router = APIRouter(prefix="/api/data-management", tags=["data-management"])

# ── 持久化存储 ──────────────────────────────────────────
_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "user_experiments.jsonl"
_lock = threading.Lock()


def _load_store() -> list[dict]:
    """从 JSONL 文件加载用户新增的实验数据"""
    if not _DATA_FILE.exists():
        return []
    records: list[dict] = []
    with open(_DATA_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _save_store(records: list[dict]) -> None:
    """将用户新增的实验数据写入 JSONL 文件"""
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _next_case_id(records: list[dict]) -> str:
    """生成下一个 case_id"""
    max_id = 0
    for r in records:
        cid = r.get("case_id", "")
        if isinstance(cid, str) and cid.startswith("user:"):
            try:
                num = int(cid.split(":")[1])
                max_id = max(max_id, num)
            except (ValueError, IndexError):
                pass
    return f"user:{max_id + 1}"


@router.get("/materials", response_model=MaterialListResponse)
def get_materials():
    """获取所有材料列表"""
    frame = load_dataset()
    existing_materials = set(frame["material"].dropna().unique())

    with _lock:
        records = _load_store()
    for record in records:
        existing_materials.add(record["material"])

    return {"materials": sorted(list(existing_materials))}


@router.post("/materials")
def create_material(material_info: MaterialInfo):
    """创建新材料"""
    if not material_info.material.strip():
        raise HTTPException(status_code=400, detail="材料名称不能为空")

    return {"message": f"材料 '{material_info.material}' 创建成功"}


@router.get("/experiments/{material}", response_model=ExperimentDataListResponse)
def get_experiment_data(material: str):
    """获取指定材料的所有实验数据"""
    frame = load_dataset()

    # 筛选指定材料的数据
    material_data = frame[frame["material"] == material]

    # 转换为字典列表
    records = []
    for _, row in material_data.iterrows():
        record = {
            "case_id": row.get("case_id"),
            "material": row.get("material"),
            "pulse_width_fs": row.get("pulse_width_fs"),
            "repetition_frequency_khz": row.get("repetition_frequency_khz"),
            "scan_speed_mm_s": row.get("scan_speed_mm_s"),
            "pulse_energy_mj": row.get("pulse_energy_mj"),
            "laser_energy_percent": row.get("laser_energy_percent"),
            "defocus_amount_mm": row.get("defocus_amount_mm"),
            "marking_count": row.get("marking_count"),
            "fill_spacing_um": row.get("fill_spacing_um"),
            "scan_interval_um": row.get("scan_interval_um"),
            "processing_time_s": row.get("processing_time_s"),
            "average_power_w": row.get("average_power_w"),
            "peak_power_kw": row.get("peak_power_kw"),
            "depth_um": row.get("depth_um"),
            "diameter_um": row.get("diameter_um"),
            "roughness_um": row.get("roughness_um"),
            "is_active": True,
            "data_source": "system" if row.get("source_file") != "feedback.jsonl" else "feedback",
            "note": None,
        }
        records.append(record)

    # 添加用户新增的数据
    with _lock:
        user_records = _load_store()
    records.extend(r for r in user_records if r["material"] == material)

    return {"records": records}


@router.post("/experiments")
def create_experiment_data(data: ExperimentData):
    """新增实验数据"""
    if not data.material.strip():
        raise HTTPException(status_code=400, detail="材料名称不能为空")

    with _lock:
        records = _load_store()
        new_record = data.model_dump(exclude_none=True)
        new_record["case_id"] = _next_case_id(records)
        records.append(new_record)
        _save_store(records)

    return {"message": "实验数据添加成功", "case_id": new_record["case_id"]}


@router.put("/experiments/{case_id}")
def update_experiment_data(case_id: str, data: ExperimentData):
    """更新实验数据"""
    with _lock:
        records = _load_store()
        for record in records:
            if record["case_id"] == case_id:
                record.update(data.model_dump(exclude_none=True))
                _save_store(records)
                return {"message": "实验数据更新成功"}

    raise HTTPException(status_code=404, detail="数据记录不存在或无法修改系统预置数据")


@router.delete("/experiments/{case_id}")
def delete_experiment_data(case_id: str):
    """删除实验数据"""
    with _lock:
        records = _load_store()
        initial_length = len(records)
        records = [r for r in records if r["case_id"] != case_id]

        if len(records) < initial_length:
            _save_store(records)
            return {"message": "实验数据删除成功"}

    raise HTTPException(status_code=404, detail="数据记录不存在或无法删除系统预置数据")
