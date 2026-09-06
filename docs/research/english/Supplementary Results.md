# Supplementary Results

Complete fixed-group test results. RMSE and MAE are in μm.

| material | target | variant | algorithm | n_development | n_test | rmse | mae | r2 |
|---|---|---|---|---|---|---|---|---|
| 4H-SiC | Depth | raw_simple | ridge | 39 | 10 | 1.874 | 1.672 | 0.130 |
| 4H-SiC | Depth | raw_complex | gaussian_process | 39 | 10 | 1.832 | 1.567 | 0.169 |
| 4H-SiC | Depth | geometry_simple | linear_regression | 39 | 10 | 2.452 | 1.997 | -0.490 |
| 4H-SiC | Depth | thermal_simple | ridge | 39 | 10 | 1.874 | 1.672 | 0.130 |
| 4H-SiC | Depth | fusion_simple | ridge | 39 | 10 | 2.234 | 1.936 | -0.237 |
| 4H-SiC | Depth | fusion_complex | decision_tree | 39 | 10 | 0.945 | 0.656 | 0.779 |
| 4H-SiC | Depth | historical_nearest | nearest_case | 39 | 10 | 2.731 | 2.047 | -0.848 |
| 4H-SiC | Roughness | raw_simple | elasticnet | 36 | 9 | 0.139 | 0.111 | 0.170 |
| 4H-SiC | Roughness | raw_complex | gaussian_process | 36 | 9 | 0.138 | 0.100 | 0.187 |
| 4H-SiC | Roughness | geometry_simple | ridge | 36 | 9 | 0.126 | 0.100 | 0.318 |
| 4H-SiC | Roughness | thermal_simple | elasticnet | 36 | 9 | 0.139 | 0.111 | 0.170 |
| 4H-SiC | Roughness | fusion_simple | ridge | 36 | 9 | 0.126 | 0.100 | 0.318 |
| 4H-SiC | Roughness | fusion_complex | svr | 36 | 9 | 0.148 | 0.108 | 0.066 |
| 4H-SiC | Roughness | historical_nearest | nearest_case | 36 | 9 | 0.218 | 0.153 | -1.034 |
| AlSiC | Depth | raw_simple | elasticnet | 87 | 25 | 10.459 | 7.609 | 0.601 |
| AlSiC | Depth | raw_complex | extra_trees | 87 | 25 | 5.876 | 3.850 | 0.874 |
| AlSiC | Depth | geometry_simple | bayesian_ridge | 87 | 25 | 4.885 | 3.709 | 0.913 |
| AlSiC | Depth | thermal_simple | elasticnet | 87 | 25 | 10.459 | 7.609 | 0.601 |
| AlSiC | Depth | fusion_simple | bayesian_ridge | 87 | 25 | 4.885 | 3.709 | 0.913 |
| AlSiC | Depth | fusion_complex | gradient_boosting | 87 | 25 | 6.532 | 4.337 | 0.844 |
| AlSiC | Depth | historical_nearest | nearest_case | 87 | 25 | 13.658 | 8.128 | 0.320 |
| AlSiC | Roughness | raw_simple | huber | 95 | 25 | 3.165 | 1.036 | 0.165 |
| AlSiC | Roughness | raw_complex | hist_gradient_boosting | 95 | 25 | 3.085 | 1.114 | 0.206 |
| AlSiC | Roughness | geometry_simple | elasticnet | 95 | 25 | 3.169 | 1.156 | 0.162 |
| AlSiC | Roughness | thermal_simple | huber | 95 | 25 | 3.165 | 1.036 | 0.165 |
| AlSiC | Roughness | fusion_simple | elasticnet | 95 | 25 | 3.169 | 1.156 | 0.162 |
| AlSiC | Roughness | fusion_complex | knn | 95 | 25 | 3.075 | 1.158 | 0.211 |
| AlSiC | Roughness | historical_nearest | nearest_case | 95 | 25 | 3.107 | 1.221 | 0.195 |
| BF33 | Depth | raw_simple | ridge | 55 | 14 | 3.185 | 2.565 | 0.070 |
| BF33 | Depth | raw_complex | random_forest | 55 | 14 | 2.285 | 1.997 | 0.521 |
| BF33 | Depth | geometry_simple | ridge | 55 | 14 | 2.187 | 1.856 | 0.561 |
| BF33 | Depth | thermal_simple | ridge | 55 | 14 | 3.185 | 2.565 | 0.070 |
| BF33 | Depth | fusion_simple | ridge | 55 | 14 | 2.187 | 1.856 | 0.561 |
| BF33 | Depth | fusion_complex | random_forest | 55 | 14 | 2.295 | 1.959 | 0.517 |
| BF33 | Depth | historical_nearest | nearest_case | 55 | 14 | 4.964 | 3.669 | -1.260 |
| BF33 | Roughness | raw_simple | huber | 56 | 14 | 0.095 | 0.067 | 0.262 |
| BF33 | Roughness | raw_complex | hist_gradient_boosting | 56 | 14 | 0.111 | 0.083 | 0.003 |
| BF33 | Roughness | geometry_simple | ridge | 56 | 14 | 0.106 | 0.071 | 0.086 |
| BF33 | Roughness | thermal_simple | huber | 56 | 14 | 0.095 | 0.067 | 0.262 |
| BF33 | Roughness | fusion_simple | ridge | 56 | 14 | 0.106 | 0.071 | 0.086 |
| BF33 | Roughness | fusion_complex | gaussian_process | 56 | 14 | 0.104 | 0.070 | 0.117 |
| BF33 | Roughness | historical_nearest | nearest_case | 56 | 14 | 0.089 | 0.063 | 0.351 |
| CFRP | Depth | raw_simple | linear_regression | 100 | 26 | 8.126 | 6.130 | 0.798 |
| CFRP | Depth | raw_complex | gradient_boosting | 100 | 26 | 4.059 | 3.300 | 0.949 |
| CFRP | Depth | geometry_simple | elasticnet | 100 | 26 | 7.531 | 5.021 | 0.826 |
| CFRP | Depth | thermal_simple | linear_regression | 100 | 26 | 8.126 | 6.130 | 0.798 |
| CFRP | Depth | fusion_simple | elasticnet | 100 | 26 | 7.531 | 5.021 | 0.826 |
| CFRP | Depth | fusion_complex | gradient_boosting | 100 | 26 | 6.290 | 4.205 | 0.879 |
| CFRP | Depth | historical_nearest | nearest_case | 100 | 26 | 13.157 | 10.046 | 0.469 |
| CFRP | Roughness | raw_simple | ridge | 102 | 26 | 0.567 | 0.466 | 0.172 |
| CFRP | Roughness | raw_complex | gaussian_process | 102 | 26 | 0.530 | 0.437 | 0.277 |
| CFRP | Roughness | geometry_simple | ridge | 102 | 26 | 0.565 | 0.454 | 0.178 |
| CFRP | Roughness | thermal_simple | ridge | 102 | 26 | 0.567 | 0.466 | 0.172 |
| CFRP | Roughness | fusion_simple | ridge | 102 | 26 | 0.565 | 0.454 | 0.178 |
| CFRP | Roughness | fusion_complex | knn | 102 | 26 | 0.543 | 0.445 | 0.241 |
| CFRP | Roughness | historical_nearest | nearest_case | 102 | 26 | 0.621 | 0.501 | 0.006 |
| SiC | Depth | raw_simple | bayesian_ridge | 95 | 23 | 25.197 | 18.940 | -0.006 |
| SiC | Depth | raw_complex | gaussian_process | 95 | 23 | 25.875 | 19.782 | -0.061 |
| SiC | Depth | geometry_simple | bayesian_ridge | 95 | 23 | 25.247 | 18.999 | -0.010 |
| SiC | Depth | thermal_simple | bayesian_ridge | 95 | 23 | 25.197 | 18.940 | -0.006 |
| SiC | Depth | fusion_simple | bayesian_ridge | 95 | 23 | 25.247 | 18.999 | -0.010 |
| SiC | Depth | fusion_complex | gaussian_process | 95 | 23 | 25.958 | 19.982 | -0.067 |
| SiC | Depth | historical_nearest | nearest_case | 95 | 23 | 31.846 | 20.753 | -0.607 |
| SiC | Roughness | raw_simple | bayesian_ridge | 96 | 24 | 2.170 | 1.767 | 0.005 |
| SiC | Roughness | raw_complex | gaussian_process | 96 | 24 | 2.229 | 1.743 | -0.050 |
| SiC | Roughness | geometry_simple | bayesian_ridge | 96 | 24 | 2.178 | 1.775 | -0.003 |
| SiC | Roughness | thermal_simple | bayesian_ridge | 96 | 24 | 2.170 | 1.767 | 0.005 |
| SiC | Roughness | fusion_simple | bayesian_ridge | 96 | 24 | 2.178 | 1.775 | -0.003 |
| SiC | Roughness | fusion_complex | gaussian_process | 96 | 24 | 2.215 | 1.768 | -0.037 |
| SiC | Roughness | historical_nearest | nearest_case | 96 | 24 | 3.231 | 2.127 | -1.206 |
| ZrO2 | Depth | raw_simple | elasticnet | 96 | 24 | 13.105 | 10.560 | 0.607 |
| ZrO2 | Depth | raw_complex | extra_trees | 96 | 24 | 6.979 | 5.142 | 0.889 |
| ZrO2 | Depth | geometry_simple | ridge | 96 | 24 | 7.852 | 6.408 | 0.859 |
| ZrO2 | Depth | thermal_simple | elasticnet | 96 | 24 | 13.105 | 10.560 | 0.607 |
| ZrO2 | Depth | fusion_simple | ridge | 96 | 24 | 7.852 | 6.408 | 0.859 |
| ZrO2 | Depth | fusion_complex | gradient_boosting | 96 | 24 | 5.891 | 4.366 | 0.921 |
| ZrO2 | Depth | historical_nearest | nearest_case | 96 | 24 | 19.181 | 14.847 | 0.158 |
| ZrO2 | Roughness | raw_simple | huber | 96 | 24 | 2.367 | 1.082 | -0.019 |
| ZrO2 | Roughness | raw_complex | svr | 96 | 24 | 2.360 | 1.078 | -0.013 |
| ZrO2 | Roughness | geometry_simple | bayesian_ridge | 96 | 24 | 2.251 | 1.110 | 0.079 |
| ZrO2 | Roughness | thermal_simple | huber | 96 | 24 | 2.367 | 1.082 | -0.019 |
| ZrO2 | Roughness | fusion_simple | bayesian_ridge | 96 | 24 | 2.251 | 1.110 | 0.079 |
| ZrO2 | Roughness | fusion_complex | svr | 96 | 24 | 2.356 | 1.085 | -0.009 |
| ZrO2 | Roughness | historical_nearest | nearest_case | 96 | 24 | 2.565 | 1.269 | -0.196 |
| Glass ceramic | Depth | raw_simple | huber | 70 | 18 | 10.170 | 6.538 | 0.098 |
| Glass ceramic | Depth | raw_complex | hist_gradient_boosting | 70 | 18 | 10.147 | 7.777 | 0.102 |
| Glass ceramic | Depth | geometry_simple | huber | 70 | 18 | 10.170 | 6.538 | 0.098 |
| Glass ceramic | Depth | thermal_simple | ridge | 70 | 18 | 10.107 | 7.029 | 0.109 |
| Glass ceramic | Depth | fusion_simple | ridge | 70 | 18 | 10.107 | 7.029 | 0.109 |
| Glass ceramic | Depth | fusion_complex | svr | 70 | 18 | 10.420 | 6.675 | 0.053 |
| Glass ceramic | Depth | historical_nearest | nearest_case | 70 | 18 | 13.074 | 9.275 | -0.491 |
| Glass ceramic | Roughness | raw_simple | linear_regression | 70 | 18 | 0.827 | 0.682 | -0.441 |
| Glass ceramic | Roughness | raw_complex | extra_trees | 70 | 18 | 0.722 | 0.369 | -0.099 |
| Glass ceramic | Roughness | geometry_simple | linear_regression | 70 | 18 | 0.827 | 0.682 | -0.441 |
| Glass ceramic | Roughness | thermal_simple | linear_regression | 70 | 18 | 0.866 | 0.660 | -0.579 |
| Glass ceramic | Roughness | fusion_simple | linear_regression | 70 | 18 | 0.866 | 0.660 | -0.579 |
| Glass ceramic | Roughness | fusion_complex | extra_trees | 70 | 18 | 0.773 | 0.373 | -0.259 |
| Glass ceramic | Roughness | historical_nearest | nearest_case | 70 | 18 | 1.324 | 0.668 | -2.695 |
| Diamond | Depth | raw_simple | linear_regression | 40 | 12 | 15.889 | 14.278 | 0.776 |
| Diamond | Depth | raw_complex | gradient_boosting | 40 | 12 | 14.377 | 11.509 | 0.816 |
| Diamond | Depth | geometry_simple | huber | 40 | 12 | 31.846 | 16.142 | 0.099 |
| Diamond | Depth | thermal_simple | linear_regression | 40 | 12 | 15.889 | 14.278 | 0.776 |
| Diamond | Depth | fusion_simple | huber | 40 | 12 | 31.846 | 16.142 | 0.099 |
| Diamond | Depth | fusion_complex | gradient_boosting | 40 | 12 | 15.403 | 10.992 | 0.789 |
| Diamond | Depth | historical_nearest | nearest_case | 40 | 12 | 23.556 | 17.920 | 0.507 |
| Diamond | Roughness | raw_simple | huber | 40 | 12 | 0.633 | 0.363 | -0.089 |
| Diamond | Roughness | raw_complex | svr | 40 | 12 | 0.627 | 0.381 | -0.069 |
| Diamond | Roughness | geometry_simple | elasticnet | 40 | 12 | 0.346 | 0.235 | 0.674 |
| Diamond | Roughness | thermal_simple | huber | 40 | 12 | 0.633 | 0.363 | -0.089 |
| Diamond | Roughness | fusion_simple | elasticnet | 40 | 12 | 0.346 | 0.235 | 0.674 |
| Diamond | Roughness | fusion_complex | svr | 40 | 12 | 0.578 | 0.332 | 0.091 |
| Diamond | Roughness | historical_nearest | nearest_case | 40 | 12 | 0.686 | 0.397 | -0.280 |
| Superalloy | Depth | raw_simple | ridge | 65 | 17 | 22.237 | 15.228 | 0.419 |
| Superalloy | Depth | raw_complex | random_forest | 65 | 17 | 19.708 | 13.360 | 0.544 |
| Superalloy | Depth | geometry_simple | ridge | 65 | 17 | 22.237 | 15.228 | 0.419 |
| Superalloy | Depth | thermal_simple | elasticnet | 65 | 17 | 20.786 | 13.589 | 0.493 |
| Superalloy | Depth | fusion_simple | elasticnet | 65 | 17 | 20.786 | 13.589 | 0.493 |
| Superalloy | Depth | fusion_complex | random_forest | 65 | 17 | 19.914 | 13.295 | 0.534 |
| Superalloy | Depth | historical_nearest | nearest_case | 65 | 17 | 19.718 | 14.338 | 0.543 |
| Superalloy | Diameter | raw_simple | huber | 65 | 17 | 90.100 | 74.427 | 0.800 |
| Superalloy | Diameter | raw_complex | hist_gradient_boosting | 65 | 17 | 122.994 | 104.555 | 0.628 |
| Superalloy | Diameter | geometry_simple | huber | 65 | 17 | 90.100 | 74.427 | 0.800 |
| Superalloy | Diameter | thermal_simple | huber | 65 | 17 | 99.935 | 81.173 | 0.755 |
| Superalloy | Diameter | fusion_simple | huber | 65 | 17 | 99.935 | 81.173 | 0.755 |
| Superalloy | Diameter | fusion_complex | hist_gradient_boosting | 65 | 17 | 125.589 | 111.288 | 0.612 |
| Superalloy | Diameter | historical_nearest | nearest_case | 65 | 17 | 174.882 | 135.809 | 0.248 |

## Scoring comparisons

| variant | tasks | satisfied | mean_normalized_error |
|---|---|---|---|
| constraint_only | 54 | 9 | 6.792 |
| constraint_uncertainty | 54 | 9 | 6.792 |
| full_score | 54 | 11 | 6.073 |