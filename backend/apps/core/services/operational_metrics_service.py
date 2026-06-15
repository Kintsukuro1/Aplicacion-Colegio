"""Metricas operativas minimas para observabilidad de API."""

from collections import defaultdict, deque
from threading import Lock


class OperationalMetricsService:
    _lock = Lock()
    _max_samples = 200
    _durations_by_endpoint = defaultdict(lambda: deque(maxlen=200))
    _status_by_endpoint = defaultdict(int)
    _total_by_endpoint = defaultdict(int)

    @classmethod
    def record_request(cls, endpoint: str, status_code: int, duration_ms: float) -> None:
        key = endpoint or 'unknown'
        bucket = f"{key}|{status_code}"
        with cls._lock:
            cls._durations_by_endpoint[key].append(max(duration_ms, 0.0))
            cls._total_by_endpoint[key] += 1
            cls._status_by_endpoint[bucket] += 1

    @classmethod
    def snapshot(cls) -> dict:
        with cls._lock:
            endpoints = sorted(cls._total_by_endpoint.keys())
            endpoint_rows = []
            total_requests = 0
            total_errors = 0

            for endpoint in endpoints:
                count = cls._total_by_endpoint[endpoint]
                total_requests += count
                status_5xx = sum(
                    v for k, v in cls._status_by_endpoint.items() if k.startswith(f"{endpoint}|") and '|5' in k
                )
                total_errors += status_5xx
                samples = list(cls._durations_by_endpoint[endpoint])
                p95 = cls._percentile(samples, 95)
                endpoint_rows.append(
                    {
                        'endpoint': endpoint,
                        'requests': count,
                        'errors_5xx': status_5xx,
                        'error_rate': round((status_5xx / count) * 100, 2) if count else 0.0,
                        'p95_ms': round(p95, 2),
                        'throughput_rps_est': round(count / 60.0, 3),
                    }
                )

            return {
                'requests_total': total_requests,
                'errors_total_5xx': total_errors,
                'error_rate_percent': round((total_errors / total_requests) * 100, 2) if total_requests else 0.0,
                'endpoints': endpoint_rows,
            }

    @staticmethod
    def _percentile(samples, percentile):
        if not samples:
            return 0.0
        ordered = sorted(samples)
        idx = int(round((percentile / 100.0) * (len(ordered) - 1)))
        idx = max(0, min(idx, len(ordered) - 1))
        return ordered[idx]
