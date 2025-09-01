"""
Memory Events Package
"""
__version__ = "1.0.2"

from .decorators.memory_events import MemoryEventHandler
from .core.shared_memory import SharedMemoryPool
from .core.events_manager import EventManager

__all__ = ['MemoryEventHandler', 'SharedMemoryPool', 'EventManager']