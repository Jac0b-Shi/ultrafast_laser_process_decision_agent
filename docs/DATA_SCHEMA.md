# 数据 Schema

## 标准字段

| 字段 | 含义 |
|---|---|
| `case_id` | 统一案例编号 |
| `material` | 材料 |
| `process_type` | 工艺类型 |
| `source_file` | 原始数据来源 |
| `source_row` | 原始表格行号 |
| `pulse_width_fs` | 脉冲宽度 |
| `repetition_frequency_khz` | 重复频率 |
| `scan_speed_mm_s` | 扫描速度 |
| `pulse_energy_mj` | 脉冲能量 |
| `defocus_amount_mm` | 离焦量 |
| `marking_count` | 标刻或加工次数 |
| `fill_spacing_um` | 填充间距 |
| `scan_interval_um` | 扫描间隔 |
| `processing_time_s` | 加工时间 |
| `average_power_w` | 平均功率 |
| `peak_power_kw` | 峰值功率 |
| `depth_um` | 加工深度 |
| `diameter_um` | 直径 |
| `roughness_um` | 表面粗糙度或 Sa |
| `raw_record` | 原始行 JSON |

## 异常值策略

- 空值保留为 `null`。
- `无法测量` 等不可数值化内容保留在 `raw_record`，标准数值列置为 `null`。
- `接近0` 在标准数值列中按 `0.0` 处理，同时原始文本保留在 `raw_record`。
