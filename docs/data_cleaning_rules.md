# Data Cleaning Rules

## Overview

Raw ultrafast laser experiment data from 5 materials is cleaned and standardized by `scripts/clean_raw_data.py`. This document records the rules applied to each dataset.

## General Rules (applied to all datasets)

| Rule | Method |
|------|--------|
| **Empty columns** | Columns with 100% null values are dropped |
| **Field naming** | Chinese column names are mapped to standardized English names (snake_case) |
| **Material label** | A `material` column is added to each dataset |
| **Column order** | Output columns follow a consistent order: identifiers → input features → output results |
| **Duplicates** | Fully duplicate rows are removed; key-field duplicates (same inputs, different outputs) are flagged in the report but retained |
| **Outliers** | Extreme outliers (beyond 3×IQR) are flagged and output to `*_anomalies.csv` — they are NOT automatically deleted |
| **Critical missing** | Rows where ALL key output columns (depth, roughness, Sa) are missing get dropped |
| **Data types** | All numeric fields are coerced to `float`/`int`; text in numeric columns triggers a conversion warning |

## Per-Dataset Rules

### 1. 4H-SiC (4H碳化硅实验数据.xlsx)

| Issue | Rule |
|-------|------|
| Column 4 (Unnamed) all-null | Dropped |
| `深度(μm)` contains "接近0" | → `0.0` |
| `深度(μm)` contains "无法测量" | → `NaN` (kept, not dropped — roughness may still be valid) |
| `粗糙度(μm)` contains "无法测量" | → `NaN` |
| **Result**: 49 rows → 49 rows, 4 roughness values NaN |

### 2. BF33 Glass (BF33实验数据.xlsx)

| Issue | Rule |
|-------|------|
| Column 4 (Unnamed) all-null | Dropped |
| `深度μm` row 63 contains "＜1" | → `NaN` (below detection limit, preserved as missing) |
| 1 roughness outlier (0.84μm) | Flagged, not removed — may be valid rough-surface measurement |
| Duplicate depth value 16.02μm | Verified as independent repeated experiment, retained |
| **Result**: 70 rows → 70 rows, 1 depth NaN |

### 3. Glass-Ceramic (微晶玻璃数据集.xlsx)

| Issue | Rule |
|-------|------|
| Column `pulse mode` misnamed | Renamed to `pulse_width_fs` (it stores pulse duration, not mode) |
| 2 depth outliers, 10 Sa outliers (3×IQR) | Flagged, not removed — glass-ceramic has inherently variable ablation |
| No missing values | Dataset is the cleanest of the five |
| **Result**: 88 rows → 88 rows, 0 missing |

### 4. Diamond (金刚石实验结果.xlsx)

| Issue | Rule |
|-------|------|
| Columns 11, 12 (Unnamed) all-null | Dropped |
| `备注` column contains experimental metadata | Extracted (2 remarks: material info, polarization mode), then column dropped |
| Individual depth measurements (深度1/2/3) | Retained as `depth_1_um`, `depth_2_um`, `depth_3_um` |
| `深度/μm` (averaged depth) | Target column; when NaN but individual measurements exist, backfill by mean |
| 8 rows missing both depth and roughness | Dropped (no usable output data) |
| 3 roughness outliers flagged | Kept (large depth variation in diamond is expected) |
| **Result**: 60 rows → 52 rows, 30 missing values (18 each in individual depth columns for non-measured samples) |

### 5. Superalloy (高温合金数据集.xlsx)

| Issue | Rule |
|-------|------|
| `Spc` column 82% missing (67/82) | Dropped — too sparse for reliable imputation |
| `Str` column 30% missing (25/82) | Imputed by `pulse_mode` group median, fallback to global median |
| 2 outlier rows (depth, Sa, Sz, depth/diameter) | Flagged, retained — extreme but physically plausible for high-fluence shots |
| **Result**: 82 rows → 82 rows, 0 missing after imputation |

## Output Structure

```
data/processed/
├── 4H_SiC_cleaned.csv              # 49 rows × 7 cols
├── BF33_cleaned.csv                 # 70 rows × 7 cols
├── BF33_cleaned_anomalies.csv       # 1 anomaly row
├── glass_ceramic_cleaned.csv        # 88 rows × 9 cols
├── glass_ceramic_cleaned_anomalies.csv  # 12 anomaly rows
├── diamond_cleaned.csv              # 52 rows × 12 cols
├── diamond_cleaned_anomalies.csv    # 3 anomaly rows
├── superalloy_cleaned.csv           # 82 rows × 17 cols
├── superalloy_cleaned_anomalies.csv # 2 anomaly rows
└── cleaning_report.txt              # Summary report
```

## Usage

```bash
python scripts/clean_raw_data.py
python scripts/clean_raw_data.py --input data/raw --output data/processed
```

## Design Principle

> Data that is **uncertain** (possibly valid, possibly erroneous) is **flagged and exported** to an anomaly file rather than silently dropped. Only data that is **definitively unusable** (all key outputs missing) is removed.
