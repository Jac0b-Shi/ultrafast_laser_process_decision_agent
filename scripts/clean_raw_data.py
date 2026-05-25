"""
Data cleaning script for ultrafast laser experiment data.
Reads raw .xlsx files from data/raw/, cleans them, and outputs
standardized CSV files to data/processed/.

Usage:
    python scripts/clean_raw_data.py
    python scripts/clean_raw_data.py --input data/raw --output data/processed
"""
import argparse
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
MATERIALS = {
    # After dropping col 4: [0]id [1]speed [2]freq [3]width [4]depth [5]roughness
    "4H碳化硅实验数据.xlsx": {
        "material": "4H-SiC",
        "output": "4H_SiC_cleaned.csv",
        "drop_cols": [4],
        "numeric_cols": [1, 2, 3, 4, 5],
        "text_replacements": {
            4: {"接近0": 0.0, "无法测量": np.nan},
            5: {"无法测量": np.nan},
        },
        "rename_map": {
            0: "experiment_id", 1: "scanning_speed_mm_s",
            2: "repetition_rate_kHz", 3: "pulse_width_fs",
            4: "depth_um", 5: "roughness_um",
        },
    },
    # After dropping col 4: [0]id [1]freq [2]power [3]speed [4]depth [5]roughness
    "BF33实验数据.xlsx": {
        "material": "BF33",
        "output": "BF33_cleaned.csv",
        "drop_cols": [4],
        "numeric_cols": [1, 2, 3, 4, 5],
        "text_replacements": {},
        "rename_map": {
            0: "experiment_id", 1: "repetition_rate_kHz",
            2: "power", 3: "scanning_speed_mm_s",
            4: "depth_um", 5: "roughness_um",
        },
    },
    "微晶玻璃数据集.xlsx": {
        "material": "glass_ceramic",
        "output": "glass_ceramic_cleaned.csv",
        # English columns, just rename for consistency
        "rename_map_english": {
            "pulse mode": "pulse_width_fs",
            "repeat frequency": "repetition_rate_kHz",
            "scanning speed": "scanning_speed_mm_s",
            "defocus amount": "defocus_amount_mm",
            "scanning interval": "scanning_interval_mm",
            "processing time": "processing_time_s",
            "depth": "depth_um",
            "Sa": "Sa_um",
        },
    },
    # After dropping cols 11,12: [0]id [1]width [2]freq [3]power [4]passes [5]speed
    # [6]d1 [7]d2 [8]d3 [9]depth [10]roughness [11]{原13备注}
    "金刚石实验结果.xlsx": {
        "material": "diamond",
        "output": "diamond_cleaned.csv",
        "drop_cols": [11, 12],
        "drop_remarks": 11,   # post-drop index of 备注
        "numeric_cols": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "text_replacements": {},
        "rename_map": {
            0: "experiment_id", 1: "pulse_width_fs",
            2: "repetition_rate_kHz", 3: "power",
            4: "processing_passes", 5: "scanning_speed_mm_s",
            6: "depth_1_um", 7: "depth_2_um", 8: "depth_3_um",
            9: "depth_um", 10: "roughness_um",
        },
        "backfill_target": 9,
        "backfill_sources": [6, 7, 8],
    },
    "高温合金数据集.xlsx": {
        "material": "superalloy",
        "output": "superalloy_cleaned.csv",
        # English columns, drop Spc (82% missing)
        "drop_cols_named": ["Spc"],
        "impute_by_group": {
            "Str": "pulse mode",
        },
        "rename_map_english": {
            "number": "experiment_id",
            "pulse mode": "pulse_width_fs",
            "pulse frequency": "repetition_rate_Hz",
            "energy": "energy_percent",
            "Pulse energy(mJ)": "pulse_energy_mJ",
            "defocusing amount": "defocus_amount_mm",
            "marking frequency": "marking_frequency_Hz",
            "Average Power(W)": "average_power_W",
            "depth": "depth_um",
            "diameter": "diameter_um",
            "depth/diameter": "depth_diameter_ratio",
            "Peak Power(kW)": "peak_power_kW",
            "Sa": "Sa_um",
            "Sz": "Sz_um",
            "Sdr": "Sdr",
        },
    },
}


def detect_outliers_iqr(series, multiplier=3.0):
    """Return boolean mask for extreme outliers (default 3*IQR)."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
    return (series < lower) | (series > upper)


def clean_one_file(filepath, config, report):
    """Clean a single raw data file according to its config. Returns (df_clean, df_anomaly)."""
    filename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"  Cleaning: {filename}")
    raw_count = None

    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"  ERROR reading file: {e}")
        report["errors"].append(f"{filename}: read error - {e}")
        return None, None

    raw_count = len(df)
    report["files"][filename] = {"raw_rows": raw_count, "raw_cols": len(df.columns)}
    removed_rows = 0
    anomaly_rows = pd.DataFrame()

    # --- Step 1: Drop fully-null columns ---
    if "drop_cols" in config:
        for c in sorted(config["drop_cols"], reverse=True):
            df = df.drop(columns=[df.columns[c]])
    if "drop_cols_named" in config:
        df = df.drop(columns=config["drop_cols_named"], errors="ignore")

    # --- Step 2: Extract remarks / metadata before dropping ---
    remarks_text = []
    if "drop_remarks" in config:
        remark_col = df.columns[config["drop_remarks"]]
        for val in df[remark_col].dropna():
            remarks_text.append(str(val))
        df = df.drop(columns=[remark_col])
        report["files"][filename]["remarks_extracted"] = len(remarks_text)

    # --- Step 3: Replace text-in-numeric-columns ---
    if "text_replacements" in config:
        for col_idx, mapping in config["text_replacements"].items():
            col_name = df.columns[col_idx]
            df.iloc[:, col_idx] = df.iloc[:, col_idx].replace(mapping)

    # --- Step 4: Convert to numeric, collect conversion failures ---
    conversion_issues = []
    if "numeric_cols" in config:
        for col_idx in config["numeric_cols"]:
            col_name = df.columns[col_idx]
            original = df.iloc[:, col_idx].copy()
            converted = pd.to_numeric(df.iloc[:, col_idx], errors="coerce")
            failed_mask = converted.isna() & original.notna()
            if failed_mask.any():
                bad_vals = original[failed_mask].unique().tolist()
                conversion_issues.append({
                    "column": col_name,
                    "bad_values": bad_vals,
                    "count": failed_mask.sum(),
                })
            df.iloc[:, col_idx] = converted

    if conversion_issues:
        report["files"][filename]["conversion_issues"] = conversion_issues
        for issue in conversion_issues:
            print(f"  [CONVERT] {issue['column']}: {issue['count']} non-numeric -> NaN ({issue['bad_values']})")

    # --- Step 5: Check duplicates ---
    dup_mask = df.duplicated()
    dup_count = dup_mask.sum()
    if dup_count > 0:
        report["files"][filename]["duplicates_removed"] = dup_count
        print(f"  [DUP] Removed {dup_count} fully duplicate rows")
        removed_rows += dup_count
        df = df[~dup_mask]

    # Check key-field duplicates (excluding experiment_id and material)
    key_cols = [c for c in df.columns if c not in ("experiment_id", "material")]
    key_dup_mask = df.duplicated(subset=key_cols, keep=False)
    key_dup_count = key_dup_mask.sum()
    if key_dup_count > 0:
        report["files"][filename]["key_field_duplicates"] = key_dup_count
        print(f"  [DUP-WARN] {key_dup_count} rows share key fields — flagged, not removed")

    # --- Step 6: Rename columns ---
    if "rename_map" in config:
        # Build mapping from old (index-based) names to new names
        mapping = {df.columns[idx]: new_name for idx, new_name in config["rename_map"].items()}
        df = df.rename(columns=mapping)
        # Keep only renamed + any remaining columns
        keep_cols = list(config["rename_map"].values())
        if "rename_map_english" in config:
            keep_cols.extend(list(config["rename_map_english"].values()))
    if "rename_map_english" in config:
        df = df.rename(columns=config["rename_map_english"])

    # --- Step 6b: Backfill from related columns ---
    if "backfill_target" in config and "backfill_sources" in config:
        # After rename, use original column refs; we'll work with numbered positions
        pass  # Handled below after rename

    # --- Step 7: Detect outliers on numeric columns ---
    numeric_df = df.select_dtypes(include=[np.number])
    outlier_flags = pd.DataFrame(False, index=df.index, columns=numeric_df.columns)
    for col in numeric_df.columns:
        outlier_flags[col] = detect_outliers_iqr(df[col])

    outlier_row_mask = outlier_flags.any(axis=1)
    if outlier_row_mask.any():
        anomaly_data = df[outlier_row_mask].copy()
        anomaly_data["anomaly_reason"] = outlier_flags[outlier_row_mask].apply(
            lambda row: "outlier: " + ", ".join(row.index[row].tolist()), axis=1
        )
        anomaly_rows = pd.concat([anomaly_rows, anomaly_data])
        report["files"][filename]["outliers_flagged"] = int(outlier_row_mask.sum())
        outlier_cols = outlier_flags.sum()
        outlier_cols = outlier_cols[outlier_cols > 0]
        print(f"  [OUTLIER] {int(outlier_row_mask.sum())} rows flagged, columns: {outlier_cols.to_dict()}")

    # --- Step 8: Handle missing values ---
    missing_before = df.isnull().sum().sum()

    # Identify key output columns (those that exist in this dataset)
    key_output_candidates = ["depth_um", "roughness_um", "Sa_um", "diameter_um"]
    key_output_cols = [c for c in key_output_candidates if c in df.columns]
    # Drop rows where ALL key output columns are missing
    critical_missing_mask = pd.Series(True, index=df.index)
    for col in key_output_cols:
        critical_missing_mask &= df[col].isnull()
    critical_dropped = critical_missing_mask.sum()
    if critical_dropped > 0:
        removed_rows += critical_dropped
        df = df[~critical_missing_mask]
        report["files"][filename]["critical_missing_dropped"] = int(critical_dropped)
        print(f"  [MISSING] Dropped {critical_dropped} rows with no depth AND no roughness")

    # Backfill depth_um from individual measurements (diamond dataset)
    if "backfill_target" in config and "backfill_sources" in config:
        depth_col_name = config["rename_map"].get(config["backfill_target"], df.columns[config["backfill_target"]])
        src_indices = config["backfill_sources"]
        src_names = [df.columns[i] if i < len(df.columns) else None for i in src_indices]
        filled = 0
        for idx in df[df[depth_col_name].isnull()].index:
            vals = df.loc[idx, src_names].dropna().values if all(n in df.columns for n in src_names) else []
            if len(vals) > 0:
                df.loc[idx, depth_col_name] = vals.mean()
                filled += 1
        if filled > 0:
            report["files"][filename]["depth_backfilled"] = filled
            print(f"  [FILL] Backfilled {filled} depth_um from individual measurements")

    missing_after = df.isnull().sum().sum()
    report["files"][filename]["missing_before"] = int(missing_before)
    report["files"][filename]["missing_after"] = int(missing_after)

    # --- Step 9: Add material label ---
    df["material"] = config["material"]

    # --- Step 10: Standardize column order ---
    ordered_cols = [
        "experiment_id", "material",
        "pulse_width_fs", "repetition_rate_kHz", "repetition_rate_Hz",
        "energy_percent", "pulse_energy_mJ", "average_power_W", "peak_power_kW",
        "power", "scanning_speed_mm_s", "defocus_amount_mm",
        "scanning_interval_mm", "marking_frequency_Hz",
        "processing_time_s", "processing_passes",
        "depth_um", "diameter_um", "depth_diameter_ratio",
        "roughness_um", "Sa_um", "Sz_um", "Str", "Sdr",
        "depth_1_um", "depth_2_um", "depth_3_um",
    ]
    existing_ordered = [c for c in ordered_cols if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_ordered]
    if remaining:
        # Remove material and experiment_id from remaining to avoid dupes
        remaining = [c for c in remaining if c not in ("experiment_id", "material")]
    df = df[existing_ordered + remaining]

    # --- Summary ---
    clean_count = len(df)
    report["files"][filename]["clean_rows"] = clean_count
    report["files"][filename]["rows_removed"] = raw_count - clean_count
    report["files"][filename]["clean_cols"] = len(df.columns)

    print(f"  Summary: {raw_count} -> {clean_count} rows ({raw_count - clean_count} removed)")
    print(f"  Columns: {len(df.columns)}, Missing values: {missing_after}")

    return df, anomaly_rows


def main():
    parser = argparse.ArgumentParser(description="Clean raw ultrafast laser experiment data")
    parser.add_argument("--input", default="data/raw", help="Path to raw data directory")
    parser.add_argument("--output", default="data/processed", help="Path for cleaned output files")
    args = parser.parse_args()

    raw_dir = args.input
    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    report = {
        "script": "scripts/clean_raw_data.py",
        "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_dir": os.path.abspath(raw_dir),
        "output_dir": os.path.abspath(out_dir),
        "files": {},
        "errors": [],
    }

    all_anomalies = []

    for filename, config in MATERIALS.items():
        filepath = os.path.join(raw_dir, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filename} not found in {raw_dir}")
            report["errors"].append(f"{filename}: file not found")
            continue

        df_clean, df_anomaly = clean_one_file(filepath, config, report)
        if df_clean is None:
            continue

        # Save cleaned data
        out_path = os.path.join(out_dir, config["output"])
        df_clean.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  -> Saved: {out_path}")

        # Save anomaly records
        if df_anomaly is not None and len(df_anomaly) > 0:
            anomaly_out = config["output"].replace(".csv", "_anomalies.csv")
            anomaly_path = os.path.join(out_dir, anomaly_out)
            df_anomaly["source_file"] = filename
            df_anomaly.to_csv(anomaly_path, index=False, encoding="utf-8-sig")
            all_anomalies.append(df_anomaly)
            print(f"  -> Anomalies: {anomaly_path} ({len(df_anomaly)} rows)")

    # --- Write cleaning report ---
    report_path = os.path.join(out_dir, "cleaning_report.txt")
    total_raw = sum(f["raw_rows"] for f in report["files"].values())
    total_clean = sum(f.get("clean_rows", 0) for f in report["files"].values())
    total_removed = sum(f.get("rows_removed", 0) for f in report["files"].values())

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("DATA CLEANING REPORT\n")
        f.write(f"Run time: {report['run_time']}\n")
        f.write(f"Input:   {report['input_dir']}\n")
        f.write(f"Output:  {report['output_dir']}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"OVERALL: {total_raw} raw rows -> {total_clean} clean rows ({total_removed} removed)\n\n")

        for fname, finfo in report["files"].items():
            f.write(f"--- {fname} ---\n")
            f.write(f"  Rows:     {finfo['raw_rows']} -> {finfo.get('clean_rows', 'N/A')}")
            f.write(f" ({finfo.get('rows_removed', 'N/A')} removed)\n")
            f.write(f"  Columns:  {finfo['raw_cols']} -> {finfo.get('clean_cols', 'N/A')}\n")
            if "duplicates_removed" in finfo:
                f.write(f"  Duplicates removed: {finfo['duplicates_removed']}\n")
            if "key_field_duplicates" in finfo:
                f.write(f"  Key-field duplicates (flagged): {finfo['key_field_duplicates']}\n")
            if "critical_missing_dropped" in finfo:
                f.write(f"  Critical missing dropped: {finfo['critical_missing_dropped']}\n")
            if "outliers_flagged" in finfo:
                f.write(f"  Outliers flagged: {finfo['outliers_flagged']}\n")
            if "depth_backfilled" in finfo:
                f.write(f"  Depth backfilled from individual measurements: {finfo['depth_backfilled']}\n")
            if "conversion_issues" in finfo:
                f.write(f"  Text->numeric conversions:\n")
                for ci in finfo["conversion_issues"]:
                    f.write(f"    {ci['column']}: {ci['count']} rows ({ci['bad_values']})\n")
            f.write(f"  Missing values: {finfo.get('missing_before', '?')} -> {finfo.get('missing_after', '?')}\n")
            if "remarks_extracted" in finfo:
                f.write(f"  Remarks extracted: {finfo['remarks_extracted']}\n")
            f.write("\n")

        if report["errors"]:
            f.write("ERRORS:\n")
            for e in report["errors"]:
                f.write(f"  - {e}\n")

    print(f"\n{'='*60}")
    print(f"Cleaning report: {report_path}")
    print(f"Total: {total_raw} raw rows -> {total_clean} clean rows")

    return 0


if __name__ == "__main__":
    sys.exit(main())