from __future__ import annotations


def iter_timestamps(duration: float, step: float):
    step = max(0.1, float(step))
    current = 0.0
    while current <= duration:
        yield current
        current += step
