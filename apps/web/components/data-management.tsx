"use client";

import { useState, useEffect } from "react";
import { Plus, Edit2, Trash2, Check, X, Database, FileText } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { ExperimentData, MaterialListResponse, ExperimentDataListResponse } from "@/types/api";

export function DataManagement() {
  const [materials, setMaterials] = useState<string[]>([]);
  const [currentMaterial, setCurrentMaterial] = useState<string>("");
  const [dataList, setDataList] = useState<ExperimentData[]>([]);
  const [newMaterialName, setNewMaterialName] = useState<string>("");
  const [editRecord, setEditRecord] = useState<ExperimentData | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const initialForm: Omit<ExperimentData, "case_id" | "material"> = {
    pulse_width_fs: null,
    repetition_frequency_khz: null,
    scan_speed_mm_s: null,
    pulse_energy_mj: null,
    laser_energy_percent: null,
    defocus_amount_mm: null,
    marking_count: null,
    fill_spacing_um: null,
    scan_interval_um: null,
    processing_time_s: null,
    average_power_w: null,
    peak_power_kw: null,
    depth_um: null,
    diameter_um: null,
    roughness_um: null,
    is_active: true,
    data_source: "user",
    note: null,
  };

  const [form, setForm] = useState<Omit<ExperimentData, "case_id" | "material">>(initialForm);

  useEffect(() => {
    fetchMaterials();
  }, []);

  useEffect(() => {
    if (currentMaterial) {
      fetchData();
    }
  }, [currentMaterial]);

  const fetchMaterials = async () => {
    try {
      const response = await apiFetch<MaterialListResponse>("/api/data-management/materials");
      setMaterials(response.materials);
    } catch (error) {
      console.error("Failed to fetch materials:", error);
      setMessage({ type: "error", text: "获取材料列表失败" });
    }
  };

  const fetchData = async () => {
    try {
      const response = await apiFetch<ExperimentDataListResponse>(`/api/data-management/experiments/${encodeURIComponent(currentMaterial)}`);
      setDataList(response.records);
    } catch (error) {
      console.error("Failed to fetch experiment data:", error);
      setMessage({ type: "error", text: "获取实验数据失败" });
    }
  };

  const createMaterial = async () => {
    if (!newMaterialName.trim()) {
      setMessage({ type: "error", text: "材料名称不能为空" });
      return;
    }

    try {
      await apiFetch("/api/data-management/materials", {
        method: "POST",
        body: JSON.stringify({ material: newMaterialName.trim() }),
      });
      setMessage({ type: "success", text: "材料创建成功" });
      setNewMaterialName("");
      fetchMaterials();
    } catch (error) {
      console.error("Failed to create material:", error);
      setMessage({ type: "error", text: "创建材料失败" });
    }
  };

  const handleSubmit = async () => {
    if (!currentMaterial) {
      setMessage({ type: "error", text: "请先选择材料" });
      return;
    }

    const body: ExperimentData = {
      ...form,
      case_id: editRecord?.case_id ?? null,
      material: currentMaterial,
    };

    try {
      if (editRecord?.case_id) {
        await apiFetch(`/api/data-management/experiments/${editRecord.case_id}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
        setMessage({ type: "success", text: "数据更新成功" });
      } else {
        await apiFetch("/api/data-management/experiments", {
          method: "POST",
          body: JSON.stringify(body),
        });
        setMessage({ type: "success", text: "数据添加成功" });
      }
      setEditRecord(null);
      setShowCreateForm(false);
      setForm(initialForm);
      fetchData();
    } catch (error) {
      console.error("Failed to save data:", error);
      setMessage({ type: "error", text: editRecord?.case_id ? "更新数据失败" : "添加数据失败" });
    }
  };

  const handleEdit = (record: ExperimentData) => {
    setEditRecord(record);
    setShowCreateForm(true);
    setForm({
      pulse_width_fs: record.pulse_width_fs,
      repetition_frequency_khz: record.repetition_frequency_khz,
      scan_speed_mm_s: record.scan_speed_mm_s,
      pulse_energy_mj: record.pulse_energy_mj,
      laser_energy_percent: record.laser_energy_percent,
      defocus_amount_mm: record.defocus_amount_mm,
      marking_count: record.marking_count,
      fill_spacing_um: record.fill_spacing_um,
      scan_interval_um: record.scan_interval_um,
      processing_time_s: record.processing_time_s,
      average_power_w: record.average_power_w,
      peak_power_kw: record.peak_power_kw,
      depth_um: record.depth_um,
      diameter_um: record.diameter_um,
      roughness_um: record.roughness_um,
      is_active: record.is_active,
      data_source: record.data_source,
      note: record.note,
    });
  };

  const handleDelete = async (caseId: string) => {
    if (!confirm("确认删除这条数据吗？")) return;

    try {
      await apiFetch(`/api/data-management/experiments/${caseId}`, {
        method: "DELETE",
      });
      setMessage({ type: "success", text: "数据删除成功" });
      fetchData();
    } catch (error) {
      console.error("Failed to delete data:", error);
      setMessage({ type: "error", text: "删除失败，可能是系统预置数据" });
    }
  };

  const handleInputChange = (field: keyof typeof form, value: string | boolean) => {
    setForm((prev) => ({
      ...prev,
      [field]: value === "" ? null : typeof value === "boolean" ? value : parseFloat(value) || null,
    }));
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case "system":
        return "系统预置";
      case "feedback":
        return "反馈数据";
      case "user":
        return "用户新增";
      default:
        return source;
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case "system":
        return "bg-gray-100 text-gray-600 border-gray-200";
      case "feedback":
        return "bg-blue-50 text-blue-600 border-blue-100";
      case "user":
        return "bg-green-50 text-green-600 border-green-100";
      default:
        return "bg-gray-50 text-gray-500 border-gray-200";
    }
  };

  const parameterFields = [
    { key: "pulse_width_fs", label: "脉冲宽度", unit: "fs" },
    { key: "repetition_frequency_khz", label: "重复频率", unit: "kHz" },
    { key: "scan_speed_mm_s", label: "扫描速度", unit: "mm/s" },
    { key: "pulse_energy_mj", label: "脉冲能量", unit: "mJ" },
    { key: "laser_energy_percent", label: "激光能量", unit: "%" },
    { key: "defocus_amount_mm", label: "离焦量", unit: "mm" },
    { key: "marking_count", label: "加工次数", unit: "" },
    { key: "fill_spacing_um", label: "填充间距", unit: "μm" },
    { key: "scan_interval_um", label: "扫描间隔", unit: "μm" },
    { key: "processing_time_s", label: "加工时间", unit: "s" },
    { key: "average_power_w", label: "平均功率", unit: "W" },
    { key: "peak_power_kw", label: "峰值功率", unit: "kW" },
  ];

  const qualityFields = [
    { key: "depth_um", label: "深度", unit: "μm" },
    { key: "diameter_um", label: "直径", unit: "μm" },
    { key: "roughness_um", label: "粗糙度", unit: "μm" },
  ];

  return (
    <div className="min-h-screen bg-[#f7f8f5]">
      {/* header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-[1440px] mx-auto px-5 flex items-center justify-between gap-4 h-16">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-white">
              <Database size={18} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">拟合数据管理</h1>
              <p className="text-xs text-gray-500">管理实验数据与材料信息</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-[1440px] mx-auto px-5 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,320px)_1fr] gap-6">
          {/* left column - materials */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">材料列表</h2>
              <p className="text-xs text-gray-500 mt-0.5">选择材料查看或管理实验数据</p>
            </div>

            <div className="p-4">
              {/* create material */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  placeholder="新材料名称"
                  value={newMaterialName}
                  onChange={(e) => setNewMaterialName(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  onKeyPress={(e) => e.key === "Enter" && createMaterial()}
                />
                <button
                  onClick={createMaterial}
                  className="flex items-center justify-center w-10 rounded-lg bg-primary text-white hover:bg-primary-800 transition-colors"
                  title="创建材料"
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* material list */}
              <div className="space-y-2">
                {materials.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">暂无材料，请先创建</p>
                ) : (
                  materials.map((material) => (
                    <button
                      key={material}
                      onClick={() => setCurrentMaterial(material)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                        currentMaterial === material
                          ? "bg-primary text-white"
                          : "bg-gray-50 text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      {material}
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* right column - data management */}
          <div className="space-y-4">
            {/* action bar */}
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900">
                {currentMaterial ? `${currentMaterial} - 实验数据` : "请选择材料"}
              </h2>
              {currentMaterial && (
                <button
                  onClick={() => {
                    setShowCreateForm(true);
                    setEditRecord(null);
                    setForm(initialForm);
                  }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-800 transition-colors"
                >
                  <Plus size={14} />
                  新增数据
                </button>
              )}
            </div>

            {/* messages */}
            {message && (
              <div
                className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
                  message.type === "success"
                    ? "bg-green-50 border border-green-100 text-green-700"
                    : "bg-red-50 border border-red-100 text-red-700"
                }`}
              >
                {message.type === "success" ? (
                  <Check size={14} className="shrink-0 mt-0.5" />
                ) : (
                  <X size={14} className="shrink-0 mt-0.5" />
                )}
                <span>{message.text}</span>
              </div>
            )}

            {/* create/edit form */}
            {showCreateForm && currentMaterial && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-gray-900">
                    {editRecord ? "编辑数据" : "新增实验数据"}
                  </h3>
                  <button
                    onClick={() => {
                      setShowCreateForm(false);
                      setEditRecord(null);
                      setForm(initialForm);
                    }}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="p-5 space-y-4">
                  {/* parameters */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">工艺参数</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                      {parameterFields.map((field) => (
                        <div key={field.key}>
                          <label className="block text-xs text-gray-500 mb-1">
                            {field.label} {field.unit && `(${field.unit})`}
                          </label>
                          <input
                            type="number"
                            step="any"
                            value={form[field.key as keyof typeof form] ?? ""}
                            onChange={(e) =>
                              handleInputChange(field.key as keyof typeof form, e.target.value)
                            }
                            placeholder="-"
                            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* quality metrics */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">输出结果</h4>
                    <div className="grid grid-cols-3 gap-3">
                      {qualityFields.map((field) => (
                        <div key={field.key}>
                          <label className="block text-xs text-gray-500 mb-1">
                            {field.label} {field.unit && `(${field.unit})`}
                          </label>
                          <input
                            type="number"
                            step="any"
                            value={form[field.key as keyof typeof form] ?? ""}
                            onChange={(e) =>
                              handleInputChange(field.key as keyof typeof form, e.target.value)
                            }
                            placeholder="-"
                            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* options */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">参与拟合</label>
                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.is_active}
                          onChange={(e) => handleInputChange("is_active", e.target.checked)}
                          className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary/20"
                        />
                        <span className="text-sm text-gray-700">{form.is_active ? "是" : "否"}</span>
                      </label>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">数据来源</label>
                      <select
                        value={form.data_source}
                        onChange={(e) => handleInputChange("data_source", e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      >
                        <option value="user">用户新增</option>
                        <option value="system">系统预置</option>
                        <option value="feedback">反馈数据</option>
                      </select>
                    </div>
                  </div>

                  {/* note */}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">备注</label>
                    <textarea
                      value={form.note ?? ""}
                      onChange={(e) => handleInputChange("note", e.target.value)}
                      placeholder="输入备注信息..."
                      rows={2}
                      className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                    />
                  </div>

                  {/* submit button */}
                  <button
                    onClick={handleSubmit}
                    className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-800 transition-colors"
                  >
                    {editRecord ? "保存修改" : "添加数据"}
                  </button>
                </div>
              </div>
            )}

            {/* data table */}
            {currentMaterial && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          工艺参数
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          输出结果
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          状态
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          来源
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          操作
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {dataList.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                            <FileText size={24} className="mx-auto mb-2 text-gray-300" />
                            <p>暂无实验数据</p>
                          </td>
                        </tr>
                      ) : (
                        dataList.map((record) => (
                          <tr key={record.case_id || Math.random()} className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="space-y-1 text-xs">
                                {record.pulse_width_fs !== null && (
                                  <p>脉宽: {record.pulse_width_fs} fs</p>
                                )}
                                {record.repetition_frequency_khz !== null && (
                                  <p>频率: {record.repetition_frequency_khz} kHz</p>
                                )}
                                {record.scan_speed_mm_s !== null && (
                                  <p>速度: {record.scan_speed_mm_s} mm/s</p>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="space-y-1 text-xs">
                                {record.depth_um !== null && <p>深度: {record.depth_um} μm</p>}
                                {record.diameter_um !== null && <p>直径: {record.diameter_um} μm</p>}
                                {record.roughness_um !== null && <p>粗糙度: {record.roughness_um} μm</p>}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                                  record.is_active
                                    ? "bg-green-50 text-green-600"
                                    : "bg-gray-100 text-gray-500"
                                }`}
                              >
                                {record.is_active ? <Check size={12} /> : <X size={12} />}
                                {record.is_active ? "参与拟合" : "已排除"}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-block px-2 py-1 rounded-full text-xs border ${getSourceColor(
                                  record.data_source
                                )}`}
                              >
                                {getSourceLabel(record.data_source)}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleEdit(record)}
                                  className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-primary transition-colors"
                                  title="编辑"
                                >
                                  <Edit2 size={14} />
                                </button>
                                {record.data_source !== "system" && (
                                  <button
                                    onClick={() => record.case_id && handleDelete(record.case_id)}
                                    className="p-1.5 rounded hover:bg-red-50 text-gray-500 hover:text-red-500 transition-colors"
                                    title="删除"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}