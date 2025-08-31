"""
InMemoryHTTPManager: Simulates HTTP request/response routing using in-memory shared memory.
"""
from typing import Callable, Dict, Any, Optional
from .shared_memory import SharedMemoryPool
from .streaming_event import StreamingEvent
import threading
import uuid

class InMemoryHTTPManager:
    """
    Provides an HTTP-like API for communication over shared memory.
    """
    def __init__(self, pool: Optional[SharedMemoryPool] = None, pool_name: str = "http_pool"):
        self.pool = pool or SharedMemoryPool(pool_name=pool_name)
        self.routes: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def route(self, path: str):
        """
        Decorator to register a route handler for a specific path.
        Usage:
            @manager.route('/foo')
            def handler(request): ...
        """
        def decorator(func):
            with self._lock:
                self.routes[path] = func
            return func
        return decorator

    def handle_request(self, path: str, method: str = "GET", data: Any = None, stream: bool = False, **kwargs) -> Any:
        """
        Handle an in-memory 'request'. Returns result or StreamingEvent.
        """
        handler = self.routes.get(path)
        if not handler:
            raise ValueError(f"Route {path} not found")
        request = {
            "method": method,
            "data": data,
            "stream": stream,
            "request_id": str(uuid.uuid4()),
            "meta": kwargs
        }
        if stream:
            stream_event = StreamingEvent(pool=self.pool, stream_key=request["request_id"])
            kwargs['stream_event'] = stream_event
            handler(request, **kwargs)
            return stream_event
        else:
            response = handler(request, **kwargs)
            return response

    def send_request(self, path: str, method: str = "GET", data: Any = None, **kwargs) -> Any:
        """
        For use by client side: simulate a request (can be read by handler).
        """
        return self.handle_request(path, method, data, **kwargs)