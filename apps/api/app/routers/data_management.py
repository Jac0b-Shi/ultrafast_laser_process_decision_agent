from fastapi import APIRouter, HTTPException

from app.schemas import ExperimentData, MaterialListResponse, ExperimentDataListResponse, MaterialInfo
from app.services.data_loader import load_dataset

router = APIRouter(prefix="/api/data-management", tags=["data-management"])

# 内存存储用户新增的数据
user_data_store: list[dict] = []


@router.get("/materials", response_model=MaterialListResponse)
def get_materials():
    """获取所有材料列表"""
    frame = load_dataset()
    existing_materials = set(frame["material"].dropna().unique())
    
    # 添加用户新增的材料
    for record in user_data_store:
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
    user_records = [r for r in user_data_store if r["material"] == material]
    records.extend(user_records)
    
    return {"records": records}


@router.post("/experiments")
def create_experiment_data(data: ExperimentData):
    """新增实验数据"""
    if not data.material.strip():
        raise HTTPException(status_code=400, detail="材料名称不能为空")
    
    new_record = data.model_dump(exclude_none=True)
    new_record["case_id"] = f"user:{len(user_data_store) + 1}"
    user_data_store.append(new_record)
    
    return {"message": "实验数据添加成功", "case_id": new_record["case_id"]}


@router.put("/experiments/{case_id}")
def update_experiment_data(case_id: str, data: ExperimentData):
    """更新实验数据"""
    # 查找并更新用户数据
    for record in user_data_store:
        if record["case_id"] == case_id:
            record.update(data.model_dump(exclude_none=True))
            return {"message": "实验数据更新成功"}
    
    raise HTTPException(status_code=404, detail="数据记录不存在或无法修改系统预置数据")


@router.delete("/experiments/{case_id}")
def delete_experiment_data(case_id: str):
    """删除实验数据"""
    global user_data_store
    initial_length = len(user_data_store)
    user_data_store = [r for r in user_data_store if r["case_id"] != case_id]
    
    if len(user_data_store) < initial_length:
        return {"message": "实验数据删除成功"}
    
    raise HTTPException(status_code=404, detail="数据记录不存在或无法删除系统预置数据")