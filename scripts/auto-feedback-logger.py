#!/usr/bin/env python3
"""
超快激光加工实验反馈日志自动生成器
=============================================
- 自动读取实验材料、目标深度/粗糙度、系统推荐参数、得分、预测值
- 录入实测深度、粗糙度，自动计算误差
- 自动生成标准化 txt 日志，保存到 experiments/实验数据反馈日志/
- 使用相对路径，自动创建文件夹，代码直接可运行

用法:
  python scripts/auto-feedback-logger.py                 交互模式
  python scripts/auto-feedback-logger.py --json '<JSON>'  JSON 输入
  python scripts/auto-feedback-logger.py --json-file <路径>  JSON 文件输入
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Fix garbled Chinese output on Windows terminals (cmd.exe defaults to GBK)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Project root discovery — mirrors apps/api/app/settings.py
# ---------------------------------------------------------------------------
def _discover_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "project9_ultrafast_laser_process_decision_agent.md").exists():
            return parent
        if (parent / "data" / "raw").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = _discover_project_root()
LOG_DIR = PROJECT_ROOT / "experiments" / "实验数据反馈日志"

# ---------------------------------------------------------------------------
# Parameter metadata: internal_name -> (Chinese label, unit)
# ---------------------------------------------------------------------------
PARAM_META: dict[str, tuple[str, str]] = {
    "pulse_width_fs":           ("脉冲宽度", "fs"),
    "repetition_frequency_khz": ("重复频率", "kHz"),
    "scan_speed_mm_s":          ("扫描速度", "mm/s"),
    "pulse_energy_mj":          ("脉冲能量", "mJ"),
    "laser_energy_percent":     ("能量档位", "%"),
    "defocus_amount_mm":        ("离焦量", "mm"),
    "marking_count":            ("加工/标记次数", ""),
    "fill_spacing_um":          ("填充间距", "μm"),
    "scan_interval_um":         ("扫描间距", "μm"),
    "processing_time_s":        ("加工时间", "s"),
    "average_power_w":          ("平均功率", "W"),
    "peak_power_kw":            ("峰值功率", "kW"),
}

# Material -> ordered list of relevant parameter keys
MATERIAL_PARAMS: dict[str, list[str]] = {
    "4H碳化硅": ["pulse_width_fs", "repetition_frequency_khz", "scan_speed_mm_s"],
    "BF33":     ["pulse_width_fs", "repetition_frequency_khz", "scan_speed_mm_s"],
    "微晶玻璃": ["pulse_width_fs", "repetition_frequency_khz", "scan_speed_mm_s",
                "defocus_amount_mm", "scan_interval_um", "processing_time_s"],
    "金刚石":   ["pulse_width_fs", "repetition_frequency_khz", "scan_speed_mm_s",
                "marking_count", "fill_spacing_um"],
    "高温合金": ["repetition_frequency_khz", "laser_energy_percent", "pulse_energy_mj",
                "defocus_amount_mm", "marking_count", "average_power_w"],
}

MATERIALS = list(MATERIAL_PARAMS.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read(prompt: str, default: str = "") -> str:
    """Read a line; return *default* when input is empty."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else str(default)
    return input(f"{prompt}: ").strip()


def _read_float(prompt: str, default: float | None = None) -> float:
    while True:
        d = str(default) if default is not None else ""
        raw = _read(prompt, d)
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print(f"  [!] 请输入有效数字，收到: {raw}")


def _fmt_val(v: float) -> str:
    """Format a numeric value cleanly — integer if possible, else strip trailing zeros."""
    if v == int(v):
        i = int(v)
        return f"{i:,}" if abs(i) >= 1000 else str(i)
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s


def _fmt_param(key: str, value: float) -> str:
    display, unit = PARAM_META.get(key, (key, ""))
    if unit:
        return f"{display}（{unit}）：{_fmt_val(value)}"
    return f"{display}：{_fmt_val(value)}"


# ---------------------------------------------------------------------------
# Data collection (interactive)
# ---------------------------------------------------------------------------
def _collect_recommendations(material: str) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    param_keys = MATERIAL_PARAMS[material]

    print("\n" + "=" * 60)
    print("  1. 录入系统推荐参数")
    print("=" * 60)

    while True:
        n = _read("\n推荐条数（回车结束本步骤）", "")
        if not n:
            break
        try:
            count = int(n)
        except ValueError:
            print("  [!] 请输入整数")
            continue

        for _ in range(count):
            idx = len(recs)
            print(f"\n--- 推荐 [{idx}] ---")
            method = _read("  生成方法 (regression / historical)", "regression")
            score = _read_float("  得分")

            params: dict[str, float] = {}
            print("  参数值（回车跳过不适用项）:")
            for key in param_keys:
                display, unit = PARAM_META[key]
                unit_hint = f"（{unit}）" if unit else ""
                raw = _read(f"    {display}{unit_hint}", "")
                if raw:
                    try:
                        params[key] = float(raw)
                    except ValueError:
                        print(f"    [!] 无效数值，跳过 {key}")

            pred_depth = _read_float("  预测深度（μm）", None)
            pred_roughness = _read_float("  预测粗糙度（μm）", None)

            recs.append({
                "method": method,
                "score": score,
                "parameters": params,
                "predicted_depth_um": pred_depth,
                "predicted_roughness_um": pred_roughness,
            })

        more = _read("\n继续添加推荐？（y/n）", "n")
        if more.lower() != "y":
            break

    return recs


def _collect_measured() -> dict[str, Any]:
    print("\n" + "=" * 60)
    print("  2. 录入实测结果")
    print("=" * 60)
    return {
        "selected_index": int(_read("选用推荐编号（0, 1, 2…）", "0")),
        "measured_depth_um": _read_float("实测加工深度（μm）"),
        "measured_roughness_um": _read_float("实测表面粗糙度（μm）"),
    }


# ---------------------------------------------------------------------------
# Log generation
# ---------------------------------------------------------------------------
def generate_log(
    material: str,
    target_depth: float,
    max_roughness: float,
    recommendations: list[dict[str, Any]],
    measured: dict[str, Any],
    operator: str = "",
    notes: str = "",
) -> str:
    today = date.today().strftime("%Y-%m-%d")
    sel = measured["selected_index"]
    m_depth = measured["measured_depth_um"]
    m_roughness = measured["measured_roughness_um"]

    lines: list[str] = []
    lines.append("# 超快激光加工实验反馈日志")
    lines.append(f"日期：{today}")
    lines.append(f"加工材料：{material}")
    parts = [f"深度{target_depth}μm"]
    parts.append(f"粗糙度≤{max_roughness}μm")
    lines.append(f"目标：{'，'.join(parts)}")

    # ---- Section 1: Recommendations ----
    if recommendations:
        lines.append("")
        lines.append("1. 系统推荐参数")
        for i, rec in enumerate(recommendations):
            label = "回归模型推荐" if rec.get("method") == "regression" else "历史案例推荐"
            lines.append(f"{label}{i}：")
            lines.append(f"得分：{rec['score']:.4f}")
            lines.append("推荐参数：")
            for key in MATERIAL_PARAMS.get(material, []):
                if key in rec.get("parameters", {}):
                    lines.append(_fmt_param(key, rec["parameters"][key]))
            if rec.get("predicted_depth_um") is not None or rec.get("predicted_roughness_um") is not None:
                lines.append("预测质量：")
                if rec.get("predicted_depth_um") is not None:
                    lines.append(f"  预测深度：{_fmt_val(rec['predicted_depth_um'])} μm")
                if rec.get("predicted_roughness_um") is not None:
                    lines.append(f"  预测粗糙度：{_fmt_val(rec['predicted_roughness_um'])} μm")
            lines.append("")

    # ---- Section 2: Measured + error analysis ----
    lines.append("2. 实测结果")
    if recommendations and sel < len(recommendations):
        rec = recommendations[sel]
        m_label = "回归模型" if rec.get("method") == "regression" else "历史案例"
        lines.append(f"选用推荐：{m_label}{sel}（得分 {rec['score']:.4f}）")
    else:
        lines.append(f"选用推荐：模型{sel}")

    lines.append(f"加工深度：{_fmt_val(m_depth)} μm")
    lines.append(f"表面粗糙度：{_fmt_val(m_roughness)} μm")

    # Error analysis
    lines.append("")
    lines.append("误差分析：")
    depth_err = m_depth - target_depth
    depth_pct = (depth_err / target_depth * 100) if target_depth else 0
    lines.append(f"  深度偏差：{depth_err:+.4f} μm（{depth_pct:+.2f}%）")
    lines.append(f"  深度绝对误差：{abs(depth_err):.4f} μm")

    r_margin = max_roughness - m_roughness
    lines.append(f"  粗糙度余量：{r_margin:+.4f} μm（上限 {max_roughness} μm）")
    if m_roughness <= max_roughness:
        lines.append("  粗糙度判定：[OK] 达标")
    else:
        over = m_roughness - max_roughness
        lines.append(f"  粗糙度判定：[X] 超标（+{over:.4f} μm）")

    if recommendations and sel < len(recommendations):
        rec = recommendations[sel]
        pred_d = rec.get("predicted_depth_um")
        pred_r = rec.get("predicted_roughness_um")
        if pred_d is not None:
            e = m_depth - pred_d
            ep = (e / pred_d * 100) if pred_d else 0
            lines.append(f"  预测深度偏差：{e:+.4f} μm（{ep:+.2f}%）")
        if pred_r is not None:
            e = m_roughness - pred_r
            ep = (e / pred_r * 100) if pred_r else 0
            lines.append(f"  预测粗糙度偏差：{e:+.4f} μm（{ep:+.2f}%）")

    # ---- Section 3: Meta ----
    lines.append("")
    lines.append("3. 反馈录入")
    if operator:
        lines.append(f"操作员：{operator}")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("本日志由 scripts/auto-feedback-logger.py 自动生成")
    if notes:
        lines.append(f"备注：{notes}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------
def save_log(content: str, material: str) -> Path:
    # Guard against path traversal (material must be a known safe value)
    if material not in MATERIAL_PARAMS:
        raise ValueError(f"Unknown material: {material}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y %m %d")
    base = f"{today} {material}.txt"
    path = LOG_DIR / base

    if path.exists():
        c = 2
        while True:
            alt = LOG_DIR / f"{today} {material}（{c}）.txt"
            if not alt.exists():
                path = alt
                break
            c += 1

    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def interactive_mode() -> None:
    print("=" * 60)
    print("  超快激光加工实验反馈日志生成器")
    print("=" * 60)

    print(f"\n项目根目录: {PROJECT_ROOT}")
    print(f"日志输出目录: {LOG_DIR}")
    print(f"\n可选材料: {', '.join(MATERIALS)}")

    while True:
        material = _read("加工材料")
        if material in MATERIAL_PARAMS:
            break
        print(f"  [!] 未知材料，可选: {', '.join(MATERIALS)}")

    target_depth = _read_float("目标深度（μm）", 5.42)
    max_roughness = _read_float("粗糙度上限（μm）", 0.45)

    recs = _collect_recommendations(material)
    if not recs:
        print("\n[!] 未录入推荐参数，将生成仅含实测结果的日志。")

    measured = _collect_measured()

    print("")
    operator = _read("操作员（可选）", "")
    notes = _read("备注（可选）", "")

    content = generate_log(
        material=material,
        target_depth=target_depth,
        max_roughness=max_roughness,
        recommendations=recs,
        measured=measured,
        operator=operator,
        notes=notes,
    )

    path = save_log(content, material)

    print("\n" + "=" * 60)
    print(f"  [OK] 日志已保存至: {path}")
    print("=" * 60)
    print("\n--- 日志预览 ---")
    print(content)


def json_mode(json_str: str) -> None:
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        sys.exit(1)

    material = data.get("material", "")
    if material not in MATERIAL_PARAMS:
        print(f"未知材料 '{material}'，可选: {', '.join(MATERIALS)}")
        sys.exit(1)

    content = generate_log(
        material=material,
        target_depth=data.get("target_depth_um", 5.42),
        max_roughness=data.get("max_roughness_um", 0.45),
        recommendations=data.get("recommendations", []),
        measured={
            "selected_index": data.get("selected_index", 0),
            "measured_depth_um": data.get("measured_depth_um", 0),
            "measured_roughness_um": data.get("measured_roughness_um", 0),
        },
        operator=data.get("operator", ""),
        notes=data.get("notes", ""),
    )

    path = save_log(content, material)
    print(f"[OK] 日志已保存至: {path}")
    print(content)


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--help", "-h"):
            print(__doc__)
        elif sys.argv[1] == "--json" and len(sys.argv) > 2:
            json_mode(sys.argv[2])
        elif sys.argv[1] == "--json-file" and len(sys.argv) > 2:
            p = Path(sys.argv[2])
            if not p.exists():
                print(f"文件不存在: {p}")
                sys.exit(1)
            json_mode(p.read_text(encoding="utf-8"))
        else:
            print(f"未知参数: {sys.argv[1]}\n使用 --help 查看帮助")
            sys.exit(1)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
