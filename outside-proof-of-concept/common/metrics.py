from __future__ import annotations
import csv, os, time, threading
from pathlib import Path

_lock = threading.Lock()

DEFAULT_COLUMNS = ["ts","run_id","component","operation","metric","value_ms","program_id","service_id"]


def project_root(start: str | Path) -> Path:
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / 'README.md').exists() and (candidate / 'launcher').exists():
            return candidate
    return Path(start).resolve()


def default_metrics_file(start: str | Path) -> Path:
    return project_root(start) / 'metrics' / 'all_metrics.csv'


def append_metric(base: str | Path, component: str, operation: str, metric: str, value_ms: float,
                  run_id: str = '', program_id: str = '', service_id: str = '', metrics_file: str | Path | None = None) -> None:
    path = Path(metrics_file) if metrics_file else default_metrics_file(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        new_file = not path.exists()
        with path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(DEFAULT_COLUMNS)
            writer.writerow([int(time.time()*1000), run_id, component, operation, metric, f"{value_ms:.6f}", program_id, service_id])
