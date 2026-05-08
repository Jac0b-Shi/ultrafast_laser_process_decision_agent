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
  line_pulse_density_pulses_mm: {
    label: "线脉冲密度 line pulse density",
    unit: "pulses/mm",
    formula: String.raw`N_L = \frac{1000f}{v}`,
    variables: "f 为重复频率 (kHz)，v 为扫描速度 (mm/s)。",
  },
  pulse_spacing_um: {
    label: "脉冲间距 pulse spacing",
    unit: "μm",
    formula: String.raw`\Delta x = \frac{1000v}{f}`,
    variables: "v 为扫描速度 (mm/s)，f 为重复频率 (kHz)。",
  },
  threshold_relative_density: {
    label: "阈值相对密度 threshold-relative density",
    unit: "ratio",
    formula: String.raw`\rho = \frac{N_L}{N_c}`,
    variables: "ρ 表示当前线脉冲密度相对同材料非零深度阈值密度的比例。",
  },
  cumulative_pulse_density: {
    label: "累积脉冲密度 cumulative pulse density",
    unit: "pulses/mm",
    formula: String.raw`N_{\mathrm{cum}} = N_L \times n`,
    variables: "由线脉冲密度与加工/标记次数 n 相乘得到。",
  },
  dose_index: {
    label: "剂量指数 dose index",
    unit: "pulses/(mm·μm)",
    formula: String.raw`I_d = \frac{N_L \times n}{h}`,
    variables: "由线脉冲密度、加工次数 n 和填充间距 h 共同构造。",
  },
  pulse_time_interaction: {
    label: "脉宽-时间交互 pulse-time interaction",
    unit: "fs·s",
    formula: String.raw`\tau t = \tau \times t`,
    variables: "τ 为脉冲宽度 (fs)，t 为加工时间 (s)。",
  },
  duty_cycle: {
    label: "占空比 duty cycle",
    unit: "ratio",
    formula: String.raw`DC = \tau \times f \times 10^{-12}`,
    variables: "τ 为脉冲宽度 (fs)，f 为重复频率 (kHz)。",
  },
  power_chain_proxy_w: {
    label: "功率链代理 power-chain proxy",
    unit: "W",
    formula: String.raw`P_{\mathrm{proxy}} = P_{\mathrm{avg}}`,
    variables: "优先使用平均功率 P_avg；缺失时由脉冲能量与重复频率构造回退代理。",
  },
  marking_energy_proxy: {
    label: "标记能量代理 marking energy proxy",
    unit: "W/count",
    formula: String.raw`E_{\mathrm{mark}} = \frac{P_{\mathrm{avg}}}{n}`,
    variables: "P_avg 为平均功率，n 为加工/标记次数。",
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
