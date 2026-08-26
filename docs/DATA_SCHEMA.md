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
| `sq_um` | 均方根粗糙度 Sq |
| `sz_um` | 最大高度 Sz |
| `min_depth_um` | 原始最小深度 |
| `max_depth_um` | 原始最大深度 |
| `quality_flags` | 质量审计标记；负深度只展示，不参加推荐 |
| `raw_record` | 原始行 JSON |

## 新增 CSV 导入

`AlSiC.csv`、`CFRP.csv`、`SiC.csv` 与 `ZrO2.csv` 使用 GB18030/GBK 解码。`间距mm` 在标准表中换算为 `fill_spacing_um`，`mean_depth_um` 和 `Sa_um` 分别映射为 `depth_um` 与 `roughness_um`。案例编号由“文件名 + 物理行号”生成，不使用原表的 `序号`，以保留 CFRP 的重复编号记录。任意 depth/min_depth/max_depth 为负时保留原始数值并添加审计标记，但不会进入对应目标的拟合、范围校验和相似案例评分。

## 推荐响应中间量

中间量只在推荐请求中即时计算，不写回原始 Excel，也不覆盖历史反馈。API 返回内部字段名，网页端统一展示为中英对照名称、单位和 KaTeX 公式。

| 字段 | 网页展示 | 公式 |
|---|---|---|
| `line_pulse_density_pulses_mm` | 线脉冲密度 line pulse density (pulses/mm) | `N_L = \frac{1000f}{v}` |
| `pulse_spacing_um` | 脉冲间距 pulse spacing (μm) | `\Delta x = \frac{v}{f}`，其中 `v` 为 mm/s、`f` 为 kHz |
| `threshold_relative_density` | 正深度参考归一化线脉冲密度 positive_depth_reference_normalized_line_pulse_density (ratio) | `\rho_+ = \frac{N_L}{N_c}` |
| `cumulative_pulse_density` | 累积脉冲密度 cumulative pulse density (pulses/mm) | `N_{\mathrm{cum}} = N_L \times n` |
| `dose_index` | 面积归一脉冲剂量代理 areal_pulse_dose_surrogate (pulses/(mm·μm)) | `I_A = \frac{N_L \times n}{h}` |
| `pulse_time_interaction` / `pulse_time_interaction_fs_s` | 候选脉宽-时间交互 pulse_time_interaction_candidate (fs·s) | `\tau t = \tau \times t` |
| `duty_cycle` | 设备占空比代理 instrument duty-cycle proxy (ratio) | `DC = \tau \times f \times 10^{-12}` |
| `power_chain_proxy_w` | 设备功率链代理 instrument power-chain proxy (W) | `P_{\mathrm{proxy}} = P_{\mathrm{avg}}` |
| `marking_energy_proxy` | 设备标记周期能量代理 instrument marking-energy proxy (J/mark) | `E_{\mathrm{mark}} = \frac{P_{\mathrm{avg}}}{f_m}` |
| `fluence_proxy_j_cm2` | 条件通量代理 fluence_proxy (J/cm²) | `F_{\mathrm{proxy}} = \frac{10^{-3}E_p}{A_{\mathrm{spot}}}`，其中 `E_p` 以 mJ 输入 |
| `average_power_density_proxy_w_cm2` | 条件平均功率密度代理 average_power_density_proxy (W/cm²) | `P_{A,\mathrm{proxy}} = \frac{P_{\mathrm{avg}}}{A_{\mathrm{spot}}}` |
| `areal_energy_density_per_mark_j_cm2` | 条件单标记周期面积能量代理 areal_energy_density_per_mark (J/cm²) | `E_{A,\mathrm{mark}} = \frac{P_{\mathrm{avg}}/f_m}{A_{\mathrm{spot}}}` |
| `pulses_per_area_per_mark` | 单次覆盖面积脉冲数代理 pulses_per_area_per_mark (pulses/mm²) | `N_{A,\mathrm{mark}} = \frac{1000N_L}{h}`；仅当 `f`、`v`、`h` 同时存在时计算，当前数据中仅金刚石满足 |
| `peak_power_kw` | 峰值功率 peak power (kW) | `P_{\mathrm{peak}}` |

说明：

- `line_pulse_density_pulses_mm`、`pulse_spacing_um`、`cumulative_pulse_density` 和 `dose_index` 是论文主叙事中的“阈值-重叠-累积”变量簇。
- `dose_index` 是内部兼容字段名，论文和展示口径统一为 `areal_pulse_dose_surrogate`；这里没有把它写作文献标准符号，因为它是本文定义的代理量。
- `threshold_relative_density` 的展示口径为 `positive_depth_reference_normalized_line_pulse_density`；`N_c` 取当前训练数据中加工深度大于 0 的 4H-SiC 记录的最小线脉冲密度，用于经验尺度归一化。
- `pulse_time_interaction` / `pulse_time_interaction_fs_s` 只作为候选交互项，需通过 `tau_only`、`t_only`、`tau_plus_t`、`tau_times_t` 消融解释。
- `duty_cycle`、`power_chain_proxy_w` 和 `marking_energy_proxy` 是设备层代理，不作为第一层物理解释。
- `fluence_proxy_j_cm2`、`average_power_density_proxy_w_cm2`、`areal_energy_density_per_mark_j_cm2` 和 `pulses_per_area_per_mark` 仅在原始字段或 `configs/research_targets.yaml` 元数据满足公式要求时计算；缺少光斑面积、hatch/填充间距等必要信息时保持 `null`/`unavailable`，不填猜测值。

## 异常值策略

- 空值保留为 `null`。
- `无法测量` 等不可数值化内容保留在 `raw_record`，标准数值列置为 `null`。
- `接近0` 在标准数值列中按 `0.0` 处理，同时原始文本保留在 `raw_record`。
