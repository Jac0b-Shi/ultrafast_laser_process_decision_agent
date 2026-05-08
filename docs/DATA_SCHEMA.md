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

## 推荐响应中间量

中间量只在推荐请求中即时计算，不写回原始 Excel，也不覆盖历史反馈。API 返回内部字段名，网页端统一展示为中英对照名称、单位和 KaTeX 公式。

| 字段 | 网页展示 | 公式 |
|---|---|---|
| `line_pulse_density_pulses_mm` | 线脉冲密度 line pulse density (pulses/mm) | `N_L = \frac{1000f}{v}` |
| `pulse_spacing_um` | 脉冲间距 pulse spacing (μm) | `\Delta x = \frac{1000v}{f}` |
| `threshold_relative_density` | 阈值相对密度 threshold-relative density (ratio) | `\rho = \frac{N_L}{N_c}` |
| `cumulative_pulse_density` | 累积脉冲密度 cumulative pulse density (pulses/mm) | `N_{\mathrm{cum}} = N_L \times n` |
| `dose_index` | 剂量指数 dose index (pulses/(mm·μm)) | `I_d = \frac{N_L \times n}{h}` |
| `pulse_time_interaction` | 脉宽-时间交互 pulse-time interaction (fs·s) | `\tau t = \tau \times t` |
| `duty_cycle` | 占空比 duty cycle (ratio) | `DC = \tau \times f \times 10^{-12}` |
| `power_chain_proxy_w` | 功率链代理 power-chain proxy (W) | `P_{\mathrm{proxy}} = P_{\mathrm{avg}}` |
| `marking_energy_proxy` | 标记能量代理 marking energy proxy (W/count) | `E_{\mathrm{mark}} = \frac{P_{\mathrm{avg}}}{n}` |
| `peak_power_kw` | 峰值功率 peak power (kW) | `P_{\mathrm{peak}}` |

## 异常值策略

- 空值保留为 `null`。
- `无法测量` 等不可数值化内容保留在 `raw_record`，标准数值列置为 `null`。
- `接近0` 在标准数值列中按 `0.0` 处理，同时原始文本保留在 `raw_record`。
