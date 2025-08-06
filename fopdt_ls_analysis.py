import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Ensure minus signs render correctly in plots
plt.rcParams['axes.unicode_minus'] = False


def fit_fopdt_for_section(df_section, time_col, mv_col, pv_col, sv_col, section_index):
    """
    Estimate FOPDT parameters for a given section using least squares.
    """
    try:
        df_section = df_section.reset_index(drop=True)

        # Skip if not enough data
        if len(df_section) < 10:
            print(f"  [실패] 구간 {section_index}: 데이터가 너무 짧습니다.")
            return None

        # Identify MV step change
        mv_diffs = df_section[mv_col].iloc[5:].diff().abs()
        if mv_diffs.isnull().all() or mv_diffs.max() < 1e-6:
            print(f"  [실패] 구간 {section_index}: MV 값에 유의미한 변화가 없습니다.")
            return None
        mv_change_idx = mv_diffs.idxmax()
        time_mv_change = df_section.loc[mv_change_idx, time_col]

        # Determine initial state
        initial_period = df_section[(df_section[time_col] < time_mv_change) &
                                    (df_section[time_col] >= time_mv_change - pd.Timedelta(seconds=30))]
        if initial_period.empty:
            initial_period = df_section.loc[:mv_change_idx-1]
        if initial_period.empty:
            print(f"  [실패] 구간 {section_index}: 초기 상태를 파악하기 위한 데이터가 부족합니다.")
            return None

        pv_initial = initial_period[pv_col].mean()
        mv_initial = initial_period[mv_col].mean()

        pv_final = df_section.iloc[-50:][pv_col].mean()
        mv_final = df_section.iloc[-50:][mv_col].mean()

        delta_pv = pv_final - pv_initial
        delta_mv = mv_final - mv_initial

        if abs(delta_mv) < 0.9:
            print(f"  [실패] 구간 {section_index}: MV 변화량({delta_mv:.2f})이 너무 작습니다.")
            return None

        # Process gain
        kp = delta_pv / delta_mv

        # Prepare data for LS fitting
        after_step_df = df_section.iloc[mv_change_idx:]
        t = (after_step_df[time_col] - time_mv_change).dt.total_seconds().to_numpy()
        y = after_step_df[pv_col].to_numpy()

        # Difference from final value
        if delta_pv > 0:
            y_diff = pv_final - y
        else:
            y_diff = y - pv_final

        mask = y_diff > 1e-3
        t_valid = t[mask]
        y_diff_valid = y_diff[mask]
        if len(t_valid) < 5:
            print(f"  [실패] 구간 {section_index}: LS 계산을 위한 유효 데이터가 부족합니다.")
            return None

        # Least squares on log-linear form
        ln_y = np.log(y_diff_valid)
        slope, intercept = np.polyfit(t_valid, ln_y, 1)
        if slope >= 0:
            print(f"  [실패] 구간 {section_index}: 유효하지 않은 기울기입니다.")
            return None

        tau = -1 / slope
        theta = (intercept - np.log(abs(pv_final - pv_initial))) * tau
        if theta < 0:
            theta = 0

        # Predict PV using the estimated parameters for R^2 calculation
        t_shifted = t - theta
        t_shifted[t_shifted < 0] = 0
        y_pred = pv_initial + kp * delta_mv * (1 - np.exp(-t_shifted / tau))

        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0

        return {
            "Section": section_index,
            "StartTime": df_section[time_col].iloc[0].strftime('%Y-%m-%d %H:%M:%S'),
            "Kp": kp,
            "tau_sec": tau,
            "theta_sec": theta,
            "R2": r_squared,
        }
    except Exception as e:
        print(f"  [실패] 구간 {section_index} 처리 중 예외 발생: {e}")
        return None


def main():
    file_path = 'FIC35085_2 (1).csv'
    time_col, pv_col, mv_col, sv_col = 'timestamp', 'PV', 'MV', 'SV'
    pre_window_sec = 30
    analysis_window_sec = 600

    try:
        df = pd.read_csv(file_path, parse_dates=[time_col])
    except FileNotFoundError:
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다. 스크립트와 동일한 폴더에 파일이 있는지 확인하세요.")
        return

    # Remove invalid initial SV values
    first_valid_sv_idx = df[sv_col].first_valid_index()
    if pd.isna(first_valid_sv_idx):
        print("SV 컬럼에 유효한 데이터가 없습니다.")
        return
    df = df.loc[first_valid_sv_idx:].reset_index(drop=True)

    # Detect SV step changes
    sv_diff = df[sv_col].diff().abs()
    step_change_indices = sv_diff[sv_diff > 20].index.tolist()

    sections = []
    for i, idx in enumerate(step_change_indices):
        step_time = df.loc[idx, time_col]
        start_time = step_time - pd.Timedelta(seconds=pre_window_sec)
        if start_time < df[time_col].iloc[0]:
            start_time = df[time_col].iloc[0]
        end_time = step_time + pd.Timedelta(seconds=analysis_window_sec)
        if i + 1 < len(step_change_indices):
            next_step_time = df.loc[step_change_indices[i+1], time_col]
            if next_step_time < end_time:
                end_time = next_step_time
        section_df = df[(df[time_col] >= start_time) & (df[time_col] < end_time)]
        if len(section_df) > 10:
            sections.append(section_df)

    print(f"SV 변화 기준, 총 {len(sections)}개의 분석 구간을 찾았습니다.")

    all_results = []
    for i, df_section in enumerate(sections, start=1):
        result = fit_fopdt_for_section(df_section, time_col, mv_col, pv_col, sv_col, section_index=i)
        if result:
            all_results.append(result)

    if all_results:
        results_df = pd.DataFrame(all_results)

        initial_count = len(results_df)
        filtered_df = results_df[(results_df['Kp'] < 80) & (results_df['Kp'] > 10) & (results_df['tau_sec'] < 300)].copy()
        num_outliers = initial_count - len(filtered_df)
        if num_outliers > 0:
            print(f"\n[알림] {num_outliers}개의 특이값 (Kp >= 80 또는 K <= 10 또는 tau_sec >= 300)을 결과에서 제외했습니다.")

        if filtered_df.empty:
            print("\n특이값 제거 후 분석할 유효한 구간이 없습니다.")
            return

        print(filtered_df.to_string(index=False))

        weights = filtered_df['R2'].clip(lower=0)
        weight_sum = weights.sum()
        if weight_sum > 0:
            norm_weights = weights / weight_sum
            avg_kp = np.average(filtered_df['Kp'], weights=norm_weights)
            avg_tau = np.average(filtered_df['tau_sec'], weights=norm_weights)
            avg_theta = np.average(filtered_df['theta_sec'], weights=norm_weights)
        else:
            avg_kp = filtered_df['Kp'].mean()
            avg_tau = filtered_df['tau_sec'].mean()
            avg_theta = filtered_df['theta_sec'].mean()

        print("\n" + "="*50)
        print("--- 대표 전달함수 (R^2 가중 평균) ---")
        print("="*50)
        print(f"  Weighted Kp    : {avg_kp:.4f}")
        print(f"  Weighted tau   : {avg_tau:.4f} sec")
        print(f"  Weighted theta : {avg_theta:.4f} sec")
        print("\n  최종 전달함수 G(s):")
        print(f" G(s) = {avg_kp:.4f} * exp(-{avg_theta:.4f}s) / ({avg_tau:.4f}s + 1)")
        print("="*50)
    else:
        print("\n분석할 유효한 구간이 없습니다.")


if __name__ == '__main__':
    main()
