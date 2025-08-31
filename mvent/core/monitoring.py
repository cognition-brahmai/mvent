"""
MonitoringTools: Utilities for reporting memory usage, event/message frequency, and handler performance metrics.
"""
import time
import threading
from typing import Dict, Callable, Any, Optional
from .shared_memory import SharedMemoryPool

class MonitoringTools:
    """
    Tracks and reports shared memory usage, event frequencies, and handler performance.
    Should be attached to managers and used in event/message processing.
    """
    def __init__(self, pool: Optional[SharedMemoryPool] = None):
        self.pool = pool or SharedMemoryPool(pool_name="monitoring_pool")
        self.event_counts: Dict[str, int] = {}
        self.handler_perf: Dict[str, Dict[str, Any]] = {}  # {name: {'calls': int, 'avg_time': float}}
        self._lock = threading.Lock()

    def record_event(self, event_name: str) -> None:
        with self._lock:
            self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1

    def record_handler_perf(self, handler_name: str, elapsed: float) -> None:
        with self._lock:
            stats = self.handler_perf.get(handler_name, {'calls': 0, 'total_time': 0.0})
            stats['calls'] += 1
            stats['total_time'] += elapsed
            stats['avg_time'] = stats['total_time'] / stats['calls']
            self.handler_perf[handler_name] = stats

    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns shared memory stats for the pool."""
        return self.pool.get_stats()

    def get_event_stats(self) -> Dict[str, int]:
        """Returns event/message frequencies."""
        return dict(self.event_counts)

    def get_handler_stats(self) -> Dict[str, Dict[str, Any]]:
        """Returns performance statistics for all handlers."""
        return dict(self.handler_perf)

    def wrap_handler(self, handler_name: str, func: Callable):
        """
        Decorator/wrapper to measure handler execution time.
        """
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            self.record_handler_perf(handler_name, elapsed)
            return result
        return wrapper