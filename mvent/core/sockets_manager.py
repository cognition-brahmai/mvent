"""
SocketsManager: Bi-directional, socket-like messaging using shared memory (RAM). Supports channels/rooms and pub/sub.
"""
import threading
import time
from typing import Callable, Any, Optional, Dict, List
from .shared_memory import SharedMemoryPool

class SocketsManager:
    """
    In-memory sockets abstraction for inter-process message exchange.
    Rooms/channels are string-based topics; messages are timestamped.
    """
    def __init__(self, pool: Optional[SharedMemoryPool] = None, pool_name: str = "sockets_pool"):
        self.pool = pool or SharedMemoryPool(pool_name=pool_name)
        self._lock = threading.Lock()
        self.subscribers: Dict[str, List[Callable]] = {}
        self._watch_threads: Dict[str, threading.Thread] = {}
        self._last_msg_index: Dict[str, int] = {}
        self._stop_flags: Dict[str, threading.Event] = {}

    def connect(self, room: str) -> None:
        """
        Ensure a room exists in shared memory.
        """
        with self._lock:
            history = self.pool.get(f"{room}:history", default=[])
            if not isinstance(history, list):
                history = []
            self.pool.set(f"{room}:history", history)

    def send(self, room: str, message: Any) -> None:
        """
        Publish a message to a room (appends to history, notifies subscribers).
        """
        with self._lock:
            history = self.pool.get(f"{room}:history", default=[])
            index = len(history)
            payload = {'index': index, 'message': message, 'timestamp': time.time()}
            history.append(payload)
            self.pool.set(f"{room}:history", history)

    def subscribe(self, room: str, callback: Callable) -> None:
        """
        Subscribe a callback to receive new messages for the room.
        """
        with self._lock:
            if room not in self.subscribers:
                self.subscribers[room] = []
            self.subscribers[room].append(callback)
        self._ensure_watching(room)

    def _ensure_watching(self, room: str):
        with self._lock:
            if room not in self._watch_threads or not self._watch_threads[room].is_alive():
                flag = threading.Event()
                self._stop_flags[room] = flag
                thread = threading.Thread(target=self._watch_room, args=(room, flag), daemon=True)
                self._watch_threads[room] = thread
                thread.start()

    def _watch_room(self, room: str, stop_flag: threading.Event):
        last_index = self._last_msg_index.get(room, -1)
        while not stop_flag.is_set():
            history = self.pool.get(f"{room}:history", default=[])
            # Deliver new messages
            for i in range(last_index + 1, len(history)):
                msg = history[i]
                for cb in self.subscribers.get(room, []):
                    try:
                        cb(msg['message'])
                    except Exception:
                        pass
                last_index = i
            self._last_msg_index[room] = last_index
            time.sleep(0.05)

    def disconnect(self, room: str) -> None:
        """
        Stop watching messages on a room/channel.
        """
        with self._lock:
            if room in self._stop_flags:
                self._stop_flags[room].set()
            if room in self._watch_threads:
                self._watch_threads[room].join(timeout=1)
            if room in self.subscribers:
                del self.subscribers[room]
            if room in self._last_msg_index:
                del self._last_msg_index[room]

    def cleanup(self):
        """
        Stop all watchers on cleanup.
        """
        for room, flag in self._stop_flags.items():
            flag.set()
        for room, thread in self._watch_threads.items():
            thread.join(timeout=1)