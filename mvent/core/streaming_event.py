"""
StreamingEvent: Shared-memory streaming event class for publish/subscribe style messaging.
"""
import threading
import queue
import time
from typing import Callable, Any, Optional, List
from .shared_memory import SharedMemoryPool

class StreamingEvent:
    """
    Streams data chunks/messages via shared memory, with listener (subscriber) support.

    Usage:
        event = StreamingEvent(pool, stream_key="foo")
        event.publish(data)
        event.subscribe(handler)
    """
    def __init__(self, pool: Optional[SharedMemoryPool] = None, stream_key: str = "default_stream"):
        self.pool = pool or SharedMemoryPool(pool_name="streaming_pool")
        self.stream_key = stream_key
        self.subscribers: List[Callable] = []
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self._watch_thread = None
        self._last_seq = 0

    def publish(self, data: Any) -> None:
        """
        Publish new data/message chunk to the stream.
        """
        with self._lock:
            timestamp = time.time()
            seq = self._last_seq + 1
            self._last_seq = seq
            payload = {'seq': seq, 'timestamp': timestamp, 'data': data}
            # Use stream_key+seq for uniqueness in pool
            self.pool.set(f"{self.stream_key}:{seq}", payload)

    def subscribe(self, callback: Callable) -> None:
        """
        Subscribe to data from the stream. Will receive all future published chunks.
        """
        with self._lock:
            self.subscribers.append(callback)
        self._ensure_watching()

    def _ensure_watching(self):
        if not self._watch_thread or not self._watch_thread.is_alive():
            self._stop_flag.clear()
            self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watch_thread.start()

    def _watch_loop(self):
        current_seq = self._last_seq
        while not self._stop_flag.is_set():
            with self._lock:
                next_seq = current_seq + 1
                payload = self.pool.get(f"{self.stream_key}:{next_seq}")
                if payload:
                    for cb in self.subscribers:
                        try:
                            cb(payload['data'])
                        except Exception:
                            pass
                    current_seq = next_seq
            time.sleep(0.05)

    def stop(self):
        self._stop_flag.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=1)