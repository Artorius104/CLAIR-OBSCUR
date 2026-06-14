"""Rate-limiting MapFunction for the PyFlink ingestion pipeline.

The actual file reading is done by PyFlink's built-in FileSource (Java-backed),
which avoids the _j_function bridge issue of a custom Python SourceFunction.
This module provides the throttle layer that sits after the source.
"""

from __future__ import annotations

import logging
import time

from pyflink.datastream.functions import MapFunction

log = logging.getLogger(__name__)

_LOG_EVERY = 100_000  # log throughput every N records


class ThrottleMap(MapFunction):
    """Pass-through MapFunction that rate-limits emission to `target_rps` rec/s.

    Uses a virtual-clock approach: compares how many records *should* have
    been emitted by now vs how many actually were, and sleeps the difference.
    Checked every 500 records to amortise the cost of time.monotonic().
    """

    def __init__(self, target_rps: int) -> None:
        self._target_rps = target_rps
        # Instance state — reset on each parallel task startup (not Flink-managed).
        self._count: int = 0
        self._start: float = 0.0

    def open(self, runtime_context) -> None:  # type: ignore[override]
        self._count = 0
        self._start = time.monotonic()
        idx = runtime_context.get_index_of_this_subtask()
        log.info("ThrottleMap[%d] open — target_rps=%d", idx, self._target_rps)

    def map(self, value: str) -> str:  # type: ignore[override]
        self._count += 1

        # Throttle: check every 500 records.
        if self._target_rps > 0 and self._count % 500 == 0:
            target_elapsed = self._count / self._target_rps
            actual_elapsed = time.monotonic() - self._start
            gap = target_elapsed - actual_elapsed
            if gap > 0.005:
                time.sleep(gap)

        # Progress log every 100k records.
        if self._count % _LOG_EVERY == 0:
            elapsed = time.monotonic() - self._start
            rps = self._count / max(elapsed, 1)
            eta_min = (14_700_000 - self._count) / max(rps, 1) / 60
            log.info(
                "ThrottleMap: %d docs | %.0f rec/s | ETA ~%.0f min",
                self._count, rps, eta_min,
            )

        return value
