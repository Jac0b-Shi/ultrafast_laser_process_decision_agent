export type MetricDisplay = {
  label: string;
  unit?: string;
  formula?: string;
  variables?: string;
  note?: string;
};

const METRIC_DISPLAY: Record<string, MetricDisplay> = {
  pulse_width_fs: {
    label: "脉冲宽度 pulse width",
    unit: "fs",
  },
  repetition_frequency_khz: {
    label: "重复频率 repetition frequency",
    unit: "kHz",
  },
  scan_speed_mm_s: {
    label: "扫描速度 scan speed",
    unit: "mm/s",
  },
  pulse_energy_mj: {
    label: "脉冲能量 pulse energy",
    unit: "mJ",
  },
  laser_energy_percent: {
    label: "能量档位 laser energy",
    unit: "%",
  },
  defocus_amount_mm: {
    label: "离焦量 defocus amount",
    unit: "mm",
  },
  marking_count: {
    label: "加工/标记次数 marking count",
  },
  fill_spacing_um: {
    label: "填充间距 fill spacing",
    unit: "μm",
  },
  scan_interval_um: {
    label: "扫描间距 scan interval",
    unit: "μm",
  },
  processing_time_s: {
    label: "加工时间 processing time",
    unit: "s",
  },
  average_power_w: {
    label: "平均功率 average power",
    unit: "W",
  },
  peak_power_kw: {
    label: "峰值功率 peak power",
    unit: "kW",
    formula: String.raw`P_{\mathrm{peak}}`,
    variables: "由高温合金表内峰值功率字段直接提供。",
  },
  depth_um: {
    label: "加工深度 depth",
    unit: "μm",
  },
  diameter_um: {
    label: "直径 diameter",
    unit: "μm",
  },
  roughness_um: {
    label: "表面粗糙度 roughness / Sa",
    unit: "μm",
  },
  sq_um: { label: "均方根粗糙度 Sq", unit: "μm" },
  sz_um: { label: "最大高度 Sz", unit: "μm" },
  min_depth_um: { label: "最小深度", unit: "μm" },
  max_depth_um: { label: "最大深度", unit: "μm" },
  line_pulse_density_pulses_mm: {
    label: "线脉冲密度 line pulse density",
    unit: "pulses/mm",
    formula: String.raw`N_L = \frac{1000f}{v}`,
    variables: "f 为重复频率 (kHz)，v 为扫描速度 (mm/s)。",
    note: "阈值-重叠-累积机制簇的核心变量。",
  },
  pulse_spacing_um: {
    label: "脉冲间距 pulse spacing",
    unit: "μm",
    formula: String.raw`\Delta x = \frac{1000v}{f}`,
    variables: "v 为扫描速度 (mm/s)，f 为重复频率 (kHz)。",
    note: "阈值-重叠-累积机制簇中扫描重叠的空间投影。",
  },
  threshold_relative_density: {
    label: "正深度参考归一化线脉冲密度 positive_depth_reference_normalized_line_pulse_density",
    unit: "ratio",
    formula: String.raw`\rho_{\mathrm{thr}} = \frac{N_L}{N_c}`,
    variables: "N_c 为当前 4H-SiC 数据中非零深度样本的经验参考；这里没有把它写成通用材料常数。",
    note: "受孵育/阈值物理启发的经验归一化代理，展示时需降调解释。",
  },
  cumulative_pulse_density: {
    label: "累积脉冲密度 cumulative pulse density",
    unit: "pulses/mm",
    formula: String.raw`N_{\mathrm{cum}} = N_L \times n`,
    variables: "由线脉冲密度与加工/标记次数 n 相乘得到。",
    note: "阈值-重叠-累积机制簇的核心变量。",
  },
  dose_index: {
    label: "面积归一脉冲剂量代理 areal_pulse_dose_surrogate",
    unit: "pulses/(mm·μm)",
    formula: String.raw`I_A = \frac{N_L \times n}{h}`,
    variables: "由线脉冲密度、加工次数 n 和填充间距 h 共同构造。",
    note: "内部字段名保持 dose_index 兼容；论文中写作 areal_pulse_dose_surrogate，是本文定义的代理量。",
  },
  pulse_time_interaction: {
    label: "候选脉宽-时间交互 pulse_time_interaction_candidate",
    unit: "fs·s",
    formula: String.raw`\tau t = \tau \times t`,
    variables: "τ 为脉冲宽度 (fs)，t 为加工时间 (s)。",
    note: "候选交互项，不作为核心机制主变量；需要与仅 τ、仅 t、τ+t 消融对照。",
  },
  pulse_time_interaction_fs_s: {
    label: "候选脉宽-时间交互 pulse_time_interaction_candidate",
    unit: "fs·s",
    formula: String.raw`\tau t = \tau \times t`,
    variables: "τ 为脉冲宽度 (fs)，t 为加工时间 (s)。",
    note: "研究管线字段；候选交互项，不作为核心机制主变量。",
  },
  duty_cycle: {
    label: "设备占空比代理 instrument duty-cycle proxy",
    unit: "ratio",
    formula: String.raw`DC = \tau \times f \times 10^{-12}`,
    variables: "τ 为脉冲宽度 (fs)，f 为重复频率 (kHz)。",
    note: "设备层代理，解释性低于扫描重叠和累积变量。",
  },
  power_chain_proxy_w: {
    label: "设备功率链代理 instrument power-chain proxy",
    unit: "W",
    formula: String.raw`P_{\mathrm{proxy}} = P_{\mathrm{avg}}`,
    variables: "优先使用平均功率 P_avg；缺失时由脉冲能量与重复频率构造回退代理。",
    note: "这里没有将其等同于 fluence 或 average power density，因为缺少光斑面积归一。",
  },
  marking_energy_proxy: {
    label: "设备标记周期能量代理 instrument marking-energy proxy",
    unit: "W/Hz",
    formula: String.raw`E_{\mathrm{mark}} = \frac{P_{\mathrm{avg}}}{f_m}`,
    variables: "P_avg 为平均功率，f_m 为标记频率。",
    note: "这里没有写成 areal energy density，因为缺少光斑面积归一。",
  },
  fluence_proxy_j_cm2: {
    label: "条件通量代理 fluence_proxy",
    unit: "J/cm²",
    formula: String.raw`F_{\mathrm{proxy}} = \frac{E_p}{A_{\mathrm{spot}}}`,
    variables: "E_p 为单脉冲能量，A_spot 来自配置中的光斑直径或半径元数据。",
    note: "仅在必要元数据可用时计算；缺失时保持 unavailable。",
  },
  average_power_density_proxy_w_cm2: {
    label: "条件平均功率密度代理 average_power_density_proxy",
    unit: "W/cm²",
    formula: String.raw`P_{A,\mathrm{proxy}} = \frac{P_{\mathrm{avg}}}{A_{\mathrm{spot}}}`,
    variables: "P_avg 为平均功率，A_spot 来自配置中的光斑直径或半径元数据。",
    note: "仅在必要元数据可用时计算；不由功率链代理猜测。",
  },
  areal_energy_density_per_mark_j_cm2: {
    label: "条件单标记周期面积能量代理 areal_energy_density_per_mark",
    unit: "J/cm²",
    formula: String.raw`E_{A,\mathrm{mark}} = \frac{P_{\mathrm{avg}}/f_m}{A_{\mathrm{spot}}}`,
    variables: "P_avg 为平均功率，f_m 为标记频率，A_spot 为光斑面积。",
    note: "仅在平均功率、标记频率和光斑面积均可用时计算。",
  },
  pulses_per_area_per_mark: {
    label: "单次覆盖面积脉冲数代理 pulses_per_area_per_mark",
    unit: "pulses/mm²",
    formula: String.raw`N_{A,\mathrm{mark}} = \frac{1000N_L}{h}`,
    variables: "N_L 为线脉冲密度，h 为 hatch、填充或扫描间距。",
    note: "仅在扫描线密度和间距字段或配置元数据可用时计算。",
  },
};

export const SCORE_FORMULAS = [
  String.raw`S = \frac{1}{1 + L},\quad L = \ell_z + \ell_\varnothing + \ell_R + 0.05m`,
  String.raw`\ell_z =
\begin{cases}
\frac{|z-z^{*}|}{s_z}, & z^{*}\ \mathrm{provided},\ z\ \mathrm{available}\\
2, & z^{*}\ \mathrm{provided},\ z\ \mathrm{missing}\\
0, & z^{*}\ \mathrm{not\ provided}
\end{cases}`,
  String.raw`\ell_\varnothing =
\begin{cases}
\frac{|\varnothing-\varnothing^{*}|}{s_\varnothing}, & \varnothing^{*}\ \mathrm{provided},\ \varnothing\ \mathrm{available}\\
2, & \varnothing^{*}\ \mathrm{provided},\ \varnothing\ \mathrm{missing}\\
0, & \varnothing^{*}\ \mathrm{not\ provided}
\end{cases}`,
  String.raw`\ell_R =
\begin{cases}
1.5, & R\ \mathrm{missing}\\
0.2\frac{R}{R_{\max}}, & R \le R_{\max}\\
1+\frac{R-R_{\max}}{R_{\max}}, & R > R_{\max}\\
0, & R_{\max}\ \mathrm{not\ provided}
\end{cases}`,
  String.raw`L_{\mathrm{default}} = R_{\mathrm{fallback}} - 0.05z + 0.05m,\quad
R_{\mathrm{fallback}} =
\begin{cases}
R, & R\ \mathrm{available}\\
1, & R\ \mathrm{missing}
\end{cases}`,
];

export const SCORE_EXPLANATION =
  "S 为最终得分，L 为综合质量损失，m 为缺失质量指标数量。z 是深度，∅ 是直径，R 是粗糙度；带 * 的量来自任务输入，s 是同材料候选集的历史标准差。填写深度、直径或粗糙度目标时使用 L 的约束分支；三个目标都未填写时使用 L_default 默认偏好分支。";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function fallbackMetricDisplay(key: string): MetricDisplay {
  let unit: string | undefined;
  let base = key;
  const suffixes: Record<string, string> = {
    _um: "μm",
    _khz: "kHz",
    _mj: "mJ",
    _kw: "kW",
    _w: "W",
    _fs: "fs",
    _s: "s",
    _mm: "mm",
  };

  for (const [suffix, suffixUnit] of Object.entries(suffixes)) {
    if (base.endsWith(suffix)) {
      base = base.slice(0, -suffix.length);
      unit = suffixUnit;
      break;
    }
  }

  return {
    label: base.replaceAll("_", " "),
    unit,
  };
}

export function getMetricDisplay(key: string): MetricDisplay {
  return METRIC_DISPLAY[key] ?? fallbackMetricDisplay(key);
}

export function metricLabel(key: string): string {
  const metric = getMetricDisplay(key);
  return metric.unit ? `${metric.label} (${metric.unit})` : metric.label;
}

export function formatMetricText(text: string): string {
  return Object.keys(METRIC_DISPLAY)
    .sort((left, right) => right.length - left.length)
    .reduce((current, key) => current.replace(new RegExp(escapeRegExp(key), "g"), metricLabel(key)), text);
}
