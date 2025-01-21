"""
Decorators for memory event handling
"""
from typing import Callable, Optional, Any
from functools import wraps
from ..core.events_manager import EventManager
from ..core.shared_memory import SharedMemoryPool

class MemoryEventHandler:
    """Handler for memory events using decorators"""
    
    def __init__(self, pool_name: str = "default_pool"):
        self.pool = SharedMemoryPool(pool_name=pool_name)
        self.event_manager = EventManager(self.pool)
    
    def on(self, event_name: str) -> Callable:
        """
        Decorator to handle memory updates
        
        @memory_events.on("user_data")
        def handle_user_update(new_value):
            print(f"User data updated: {new_value}")
        """
        def decorator(func: Callable) -> Callable:
            self.event_manager.subscribe(event_name, func)
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def emit(self, event_name: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Emit an event by updating shared memory
        
        memory_events.emit("user_data", {"name": "John"})
        """
        self.pool.set(event_name, value, ttl=ttl)
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.event_manager.stop()
        self.pool.cleanup()