from collections import defaultdict
from typing import Any


class MetricsCollector:
    """Simple in-memory metrics collector (counters + timings)."""

    def __init__(self):
        self._counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._timings: dict[str, list[float]] = defaultdict(list)

    def increment(self, metric: str, tags: dict[str, str] | None = None) -> None:
        key = _metric_key(metric, tags)
        self._counters[metric][key] += 1

    def get_counter(self, metric: str, tags: dict[str, str] | None = None) -> int:
        key = _metric_key(metric, tags)
        return self._counters[metric].get(key, 0)

    def record(self, metric: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = _metric_key(metric, tags)
        self._timings[key].append(value)

    def get_latest(self, metric: str, tags: dict[str, str] | None = None) -> float:
        key = _metric_key(metric, tags)
        vals = self._timings.get(key, [])
        return vals[-1] if vals else 0.0

    def summary(self) -> dict[str, Any]:
        result = {}
        for metric, keys in self._counters.items():
            result[metric] = {}
            for key, val in keys.items():
                result[metric][key] = val
        for key, vals in self._timings.items():
            metric = key.split("[")[0] if "[" in key else key
            if metric not in result:
                result[metric] = {}
            result[metric][f"{key}:last"] = vals[-1] if vals else 0
            result[metric][f"{key}:avg"] = sum(vals) / len(vals) if vals else 0
        return result


def _metric_key(metric: str, tags: dict[str, str] | None = None) -> str:
    if not tags:
        return metric
    tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return f"{metric}[{tag_str}]"
