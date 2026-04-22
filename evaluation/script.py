import sys
from datetime import datetime

import pandas as pd
import numpy as np
from scipy.stats import shapiro, mannwhitneyu


class TeeLogger:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> None:
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def extract_metric(df: pd.DataFrame, metric: str, component: str = "integration_process") -> np.ndarray:
    return df[(df["component"] == component) & (df["metric"] == metric)]["value_ms"].astype(float).to_numpy()


def mean_std(x: np.ndarray) -> tuple[float, float]:
    return float(np.mean(x)), float(np.std(x, ddof=1))


def cliff_delta(x: np.ndarray, y: np.ndarray) -> float:
    n = len(x) * len(y)
    greater = sum(i > j for i in x for j in y)
    less = sum(i < j for i in x for j in y)
    return (greater - less) / n


def holm_correction(p_values: list[float]) -> list[float]:
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda t: t[1])
    adjusted = [0.0] * m
    prev = 0.0
    for rank, (idx, p) in enumerate(indexed, start=1):
        value = (m - rank + 1) * p
        value = max(value, prev)
        adjusted[idx] = min(value, 1.0)
        prev = adjusted[idx]
    return adjusted


def iqr_filter(x: np.ndarray) -> np.ndarray:
    q1 = np.percentile(x, 25)
    q3 = np.percentile(x, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return x[(x >= lower) & (x <= upper)]


def contribution(operation_mean: float, total_mean: float) -> float:
    if total_mean == 0:
        return 0.0
    return 100.0 * operation_mean / total_mean


def analyse_main_comparison(inside_csv: str, outside_csv: str) -> None:
    inside = load_csv(inside_csv)
    outside = load_csv(outside_csv)

    metrics = ["read_act_total_ms", "execute_total_ms"]
    raw_p = []

    print("=== Main comparison: trusted vs conventional ===")
    for metric in metrics:
        x = extract_metric(inside, metric)
        y = extract_metric(outside, metric)

        mean_x, std_x = mean_std(x)
        mean_y, std_y = mean_std(y)

        p_shapiro_x = shapiro(x).pvalue
        p_shapiro_y = shapiro(y).pvalue

        _, p_mw = mannwhitneyu(x, y, alternative="two-sided")
        raw_p.append(p_mw)

        delta = cliff_delta(x, y)

        print(f"\nMetric: {metric}")
        print(f"Trusted mean ± std: {mean_x:.2f} ± {std_x:.2f}")
        print(f"Conventional mean ± std: {mean_y:.2f} ± {std_y:.2f}")
        print(f"Shapiro trusted: {p_shapiro_x:.6f}")
        print(f"Shapiro conventional: {p_shapiro_y:.6f}")
        print(f"Mann–Whitney raw p-value: {p_mw:.6f}")
        print(f"Cliff's Delta: {delta:.3f}")

    adjusted = holm_correction(raw_p)
    for metric, p_adj in zip(metrics, adjusted):
        print(f"Holm-adjusted p-value for {metric}: {p_adj:.6f}")

    print("\n=== Robustness analysis after IQR filtering ===")
    for metric in metrics:
        x = extract_metric(inside, metric)
        y = extract_metric(outside, metric)
        xf = iqr_filter(x)
        yf = iqr_filter(y)

        mean_xf, std_xf = mean_std(xf)
        mean_yf, std_yf = mean_std(yf)

        print(f"\nMetric: {metric}")
        print(f"Trusted mean ± std without outliers: {mean_xf:.2f} ± {std_xf:.2f}")
        print(f"Conventional mean ± std without outliers: {mean_yf:.2f} ± {std_yf:.2f}")
        print(f"Trusted outliers removed: {len(x) - len(xf)}")
        print(f"Conventional outliers removed: {len(y) - len(yf)}")


def analyse_trusted_internal_cost(inside_csv: str) -> None:
    inside = load_csv(inside_csv)

    read_ops = [
        ("lookupService_ms", "Service lookup"),
        ("getCertificate_ms", "Certificate retrieval"),
        ("getProgramPublicKey_ms", "Public-key retrieval"),
        ("decrypt_ms", "Local decryption"),
    ]

    start_ops = [
        ("retrieveProgram_ms", "Source-code retrieval"),
        ("compile_ms", "Compilation"),
        ("createCompartment_ms", "Compartment creation"),
        ("deploy_ms", "Deployment"),
        ("getIntegratedServices_ms", "Integrated-services retrieval"),
        ("exchangeKeys_ms", "Key exchange"),
        ("generateAttestableDoc_ms", "Attestable-document generation"),
        ("generateCertificate_ms", "Certificate generation"),
        ("sign_ms", "Certificate signing"),
        ("run_ms", "Program execution"),
        ("start_total_ms", "Launcher.start()"),
    ]

    read_total = extract_metric(inside, "read_act_total_ms")
    read_total_mean = np.mean(read_total)

    print("\n=== Internal cost of Read_act in the trusted environment ===")
    for metric, label in read_ops:
        component = "launcher" if metric != "decrypt_ms" else "integration_process"
        values = extract_metric(inside, metric, component=component)
        if len(values) == 0:
            print(f"{label}: no data")
            continue
        m = float(np.mean(values))
        c = contribution(m, read_total_mean)
        print(f"{label}: mean={m:.6f} ms, contribution={c:.3f}%")

    print(f"Read_act total mean: {read_total_mean:.6f} ms")

    print("\n=== Internal cost of Launcher.start() in the trusted environment ===")
    for metric, label in start_ops:
        values = extract_metric(inside, metric, component="launcher")
        if len(values) == 0:
            print(f"{label}: no data")
            continue
        m = float(np.mean(values))
        print(f"{label}: mean={m:.6f} ms")


if __name__ == "__main__":
    INSIDE_CSV = "inside.csv"
    OUTSIDE_CSV = "outside.csv"
    LOG_FILE = "analysis_results.log"

    original_stdout = sys.stdout
    with open(LOG_FILE, "w", encoding="utf-8") as log_file:
        sys.stdout = TeeLogger(original_stdout, log_file)
        try:
            print(f"Analysis started at: {datetime.now().isoformat(timespec='seconds')}")
            print(f"Inside CSV: {INSIDE_CSV}")
            print(f"Outside CSV: {OUTSIDE_CSV}")
            print(f"Log file: {LOG_FILE}\n")

            analyse_main_comparison(INSIDE_CSV, OUTSIDE_CSV)
            analyse_trusted_internal_cost(INSIDE_CSV)

            print(f"\nAnalysis finished at: {datetime.now().isoformat(timespec='seconds')}")
        finally:
            sys.stdout = original_stdout

    print(f"Results were also saved to: {LOG_FILE}")