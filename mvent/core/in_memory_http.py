"""
InMemoryHTTPManager: Simulates HTTP request/response routing using in-memory shared memory.
"""
from typing import Callable, Dict, Any, Optional
from .shared_memory import SharedMemoryPool
from .streaming_event import StreamingEvent
import threading
import uuid
import os
import time


class InMemoryHTTPManager:
    """
    Provides an HTTP-like API for communication over shared memory.

    GLOBAL ENDPOINTS BEHAVIOR:
        - HTTP endpoints ("routes") registered via @route(path) become discoverable by *all* processes attached to
          the same SharedMemoryPool, thanks to global route metadata written to the pool.
        - Use .get_routes() to see every endpoint registered globally (i.e., by all processes).
        - Actual handler functions remain process-local: only a process that registered a route
          can service its requests. No code is transmitted cross-process.
        - For fully distributed service, at least one process with each route handler must be running
          and able to pick up/handle logical requests for that endpoint.
        - Global registry enables cooperative distributed HTTP-like service orchestration across workers.
        - Design pattern: pool acts as a coordination/broker layer for multiprocess distributed HTTP API.

    Example pattern (for cooperative worker servers):
        1. Each worker process registers its HTTP endpoints with @route(path), which stores route meta in the pool.
        2. Use get_routes() from any process to rediscover available endpoints. Clients may pick dynamically.
        3. Requests must be serviced by processes with the handler code available.
        4. Actual work distribution could be implemented by posting work items in the pool.

    """
    def __init__(self, pool: Optional[SharedMemoryPool] = None, pool_name: str = "http_pool"):
        self.pool = pool or SharedMemoryPool(pool_name=pool_name)
        self.routes: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self.pid = os.getpid()

    def route(self, path: str):
        """
        Decorator to register a route handler for a specific path.
        Registers metadata in shared memory for global route lookup.
        Usage:
            @manager.route('/foo')
            def handler(request): ...
        """
        def decorator(func):
            with self._lock:
                self.routes[path] = func
                # Register route metadata globally – any process can see registered endpoints
                meta = {
                    "registered_by": self.pid,
                    "handler_name": func.__name__,
                    "handler_module": func.__module__,
                    "timestamp": time.time()
                }
                self.pool.set(f"http_route:{path}", meta)
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
    def get_routes(self):
        """
        Returns global dict of all HTTP endpoints visible to this pool.
        Key: route path, Value: route metadata dict.
        """
        all_records = self.pool.get_all()
        routes = {}
        for k, v in all_records.items():
            if k.startswith("http_route:"):
                routes[k[len("http_route:"):]] = v
        return routes
