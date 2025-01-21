"""
Event management system for shared memory events
"""
from typing import Dict, Set, Callable, Any
import threading
import time
import logging
from .shared_memory import SharedMemoryPool

logger = logging.getLogger(__name__)

class EventManager:
    """Manages event subscriptions and triggers for shared memory events"""
    
    def __init__(self, pool: SharedMemoryPool):
        self.pool = pool
        self.subscribers: Dict[str, Set[Callable]] = {}
        self._watch_thread = None
        self._stop_watch = threading.Event()
        self._last_values: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe a callback to an event"""
        with self._lock:
            if event_name not in self.subscribers:
                self.subscribers[event_name] = set()
            self.subscribers[event_name].add(callback)
            
        # Start watching if not already started
        self._ensure_watching()
    
    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe a callback from an event"""
        with self._lock:
            if event_name in self.subscribers:
                self.subscribers[event_name].discard(callback)
                if not self.subscribers[event_name]:
                    del self.subscribers[event_name]
    
    def _ensure_watching(self) -> None:
        """Ensure the watch thread is running"""
        if not self._watch_thread or not self._watch_thread.is_alive():
            self._stop_watch.clear()
            self._watch_thread = threading.Thread(
                target=self._watch_loop,
                daemon=True,
                name="memory_event_watcher"
            )
            self._watch_thread.start()
    
    def _watch_loop(self) -> None:
        """Watch for changes in subscribed memory locations"""
        while not self._stop_watch.is_set():
            try:
                with self._lock:
                    for event_name in list(self.subscribers.keys()):
                        current_value = self.pool.get(event_name)
                        last_value = self._last_values.get(event_name)
                        
                        if current_value != last_value:
                            self._last_values[event_name] = current_value
                            # Trigger callbacks
                            for callback in list(self.subscribers[event_name]):
                                try:
                                    callback(current_value)
                                except Exception as e:
                                    logger.error(f"Error in callback for {event_name}: {e}")
            
            except Exception as e:
                logger.error(f"Error in event watch loop: {e}")
            
            time.sleep(0.1)  # Small delay to prevent CPU overuse
    
    def stop(self) -> None:
        """Stop the event manager"""
        self._stop_watch.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=1.0)