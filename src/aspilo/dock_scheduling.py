from __future__ import annotations
import heapq
import hashlib
import pandas as pd


def _stable_unit_interval(text: str) -> float:
    """Deterministic pseudo-random number in [0, 1) from text."""
    raw = hashlib.sha256(text.encode('utf-8')).digest()[:8]
    return int.from_bytes(raw, 'big') / 2**64


def schedule_receiving(
    routes: pd.DataFrame,
    n_docks: int = 5,
    start_hour: float = 6.0,
    close_hour: float = 18.0,
    stagger: bool = True,
) -> pd.DataFrame:
    """Greedy finite-dock schedule with deterministic requested arrivals.

    Routes with high frequency and long service are placed first.  When ``stagger``
    is enabled, requested arrivals are spread over the receiving window before
    finite-dock list scheduling is applied.  This is a transparent scheduling
    heuristic, not a claim of globally optimal dock assignment.
    """
    docks = [(start_hour, i) for i in range(n_docks)]
    heapq.heapify(docks)
    rows = []
    ordered = routes.sort_values(['frequency_per_week', 'route_duration_h'], ascending=[False, False])
    receiving_span = max(1.0, close_hour - start_hour - 1.0)
    for pos, (_, r) in enumerate(ordered.iterrows()):
        available, dock = heapq.heappop(docks)
        if stagger:
            # low-discrepancy-like deterministic staggering, with a small stable route offset
            frac = ((pos * 0.6180339887498949) + 0.12 * _stable_unit_interval(str(r.route_id))) % 1.0
            requested = start_hour + frac * receiving_span
        else:
            requested = start_hour + _stable_unit_interval(str(r.route_id)) * receiving_span
        start = max(available, requested)
        service = 0.25 + 0.08 * float(r.n_stops) + 0.0025 * float(r.load_cube_m3)
        wait = max(0.0, start - requested)
        end = start + service
        overtime = max(0.0, end - close_hour)
        heapq.heappush(docks, (end, dock))
        rows.append((r.route_id, dock, requested, start, end, wait, service, overtime))
    return pd.DataFrame(rows, columns=[
        'route_id', 'dock_id', 'requested_arrival_h', 'scheduled_start_h',
        'scheduled_end_h', 'waiting_h', 'dock_service_h', 'overtime_h'
    ])
