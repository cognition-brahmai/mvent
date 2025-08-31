# mvent Documentation

## Overview

**mvent** is a Python package that enables event-driven, shared memory communication between processes. It provides a simple, decorator-based API for registering event handlers and emitting events, making inter-process communication (IPC) seamless and efficient. The package is designed for scenarios where multiple processes need to share data and react to changes in real time, such as in distributed systems, parallel computing, or multi-process applications.

### Key Features

- **Shared memory communication** using memory-mapped files
- **Event-driven architecture** with decorator-based handlers
- **TTL (Time-To-Live) support** for temporary data
- **Automatic cleanup** of expired or orphaned data
- **Thread-safe operations**
- **Multiple handlers** per event

---

## Architecture

mvent consists of three main components:

### 1. SharedMemoryPool

- Manages a memory-mapped file for storing key-value pairs accessible by multiple processes.
- Supports TTL for entries, automatic cleanup of expired data, and statistics reporting.
- Thread-safe via internal locking.
- Serializes data using Python's `pickle` module.
- Background thread for periodic cleanup.

### 2. EventManager

- Manages event subscriptions and triggers callbacks when shared memory values change.
- Uses a background watcher thread to monitor changes in shared memory.
- Supports subscribing and unsubscribing handlers for named events.
- Ensures thread safety for event operations.

### 3. MemoryEventHandler

- User-facing API for registering event handlers and emitting events.
- Provides the `@on(event_name)` decorator for handler registration.
- Provides the `emit(event_name, value, ttl=None)` method to update shared memory and trigger events.
- Handles resource cleanup via `cleanup()`.

---

## Extended Architecture

The mvent library now supports a comprehensive suite of in-memory IPC patterns:

### 4. InMemoryHTTPManager
- Simulates HTTP-like request/response routing fully in shared memory (RAM).
- Allows registration of route handlers (`@manager.route("/foo")`).
- Supports both regular and streaming (chunked/real-time) responses.

### 5. StreamingEvent
- Provides shared-memory pub/sub streaming for chunked or live data.
- Suited to observable real-time sources.

### 6. SocketsManager
- Implements in-RAM socket-like bi-directional communication.
- Supports "rooms"/channels, pub/sub, and history.

### 7. MonitoringTools
- Tracks memory usage, event/message frequencies, and callback performance metrics.
- Integrates with all core and advanced managers.

### 8. Security: Shared Memory Encryption
- Optional end-to-end encryption for all memory pool data.
- Uses symmetric keys (Fernet/AES) for secure data at rest with fallback to plaintext.

---



## API Reference

### MemoryEventHandler

```python
from mvent import MemoryEventHandler

memory_events = MemoryEventHandler("my_pool")
```

- **on(event_name: str) -> Callable**
  - Decorator to register a handler for an event.
  - Example:
    ```python
    @memory_events.on("user_data")
    def handle_user_update(new_value):
        print(f"User data updated: {new_value}")
    ```

- **emit(event_name: str, value: Any, ttl: Optional[float] = None) -> None**
  - Emit an event by updating shared memory.
  - Example:
    ```python
    memory_events.emit("user_data", {"name": "John"}, ttl=5.0)
    ```

- **cleanup() -> None**
  - Cleans up resources and stops background threads.

### SharedMemoryPool

- **set(name: str, value: Any, ttl: Optional[float] = None) -> bool**
  - Set a value in the shared memory pool.

- **get(name: str, default: Any = None, with_metadata: bool = False) -> Any**
  - Get a value from the shared memory pool.

- **delete(name: str) -> bool**
  - Delete a value from the shared memory pool.

- **clear() -> None**
  - Clear all data from the shared memory pool.

- **get_all() -> Dict[str, Any]**
  - Get all key-value pairs.

- **get_stats() -> Dict[str, Any]**
  - Get statistics about the memory pool.

- **cleanup() -> None**
  - Stop cleanup thread and perform shutdown maintenance.

### EventManager

- **subscribe(event_name: str, callback: Callable) -> None**
  - Subscribe a callback to an event.

- **unsubscribe(event_name: str, callback: Callable) -> None**
  - Unsubscribe a callback from an event.

- **stop() -> None**
  - Stop the event manager's watcher thread.

---
### Advanced Example: InMemoryHTTPManager

```python
from mvent.core.in_memory_http import InMemoryHTTPManager

http = InMemoryHTTPManager()

@http.route("/greet")
def greet_handler(request):
    data = request["data"]
    return {"greeting": f"Hello, {data['name']}!"}

# Simulate a request
resp = http.send_request("/greet", method="POST", data={"name": "Alice"})
print(resp)  # {'greeting': 'Hello, Alice!'}
```

### Advanced Example: StreamingEvent

```python
from mvent.core.streaming_event import StreamingEvent

stream = StreamingEvent(stream_key="chatroom1")

def on_message(msg):
    print("STREAMED:", msg)

stream.subscribe(on_message)
stream.publish("Welcome to the room!")
```

### Advanced Example: SocketsManager

```python
from mvent.core.sockets_manager import SocketsManager

sockets = SocketsManager()
def print_msg(m): print("Room got:", m)
sockets.connect("room1")
sockets.subscribe("room1", print_msg)
sockets.send("room1", "This is in RAM only!")
```

### Advanced Example: Monitoring and Security

```python
from mvent.core.monitoring import MonitoringTools
from mvent.core.shared_memory import SharedMemoryPool
from cryptography.fernet import Fernet

key = Fernet.generate_key()
secure_pool = SharedMemoryPool("secure", encryption_key=key)
monitor = MonitoringTools(pool=secure_pool)

@monitor.wrap_handler("example", lambda x: x * x)
def square(x): return x*x

monitor.record_event("test_event")
monitor.wrap_handler("timed", square)(4)
print(monitor.get_event_stats())
print(monitor.get_handler_stats())
print("Secure stats:", monitor.get_memory_stats())
```
---

## Usage Examples

### Basic Usage

```python
from mvent import MemoryEventHandler
import time

memory_events = MemoryEventHandler("my_pool")

@memory_events.on("user_data")
def handle_user_update(new_value):
    print(f"User data updated: {new_value}")

memory_events.emit("user_data", {"name": "John", "age": 30})
time.sleep(1)
memory_events.cleanup()
```

### Multiple Handlers

```python
@memory_events.on("user_data")
def log_user_update(new_value):
    print(f"Logging: {new_value}")

@memory_events.on("user_data")
def process_user_update(new_value):
    # Process the data
    pass
```

### Using TTL

```python
memory_events.emit("temporary_data", "This will expire", ttl=60.0)
```

### Full Example

```python
def main():
    memory_events = MemoryEventHandler("example_pool")

    @memory_events.on("user_data")
    def handle_user_update(new_value):
        print(f"Received user data update: {new_value}")

    @memory_events.on("user_data")
    def log_user_update(new_value):
        print(f"Logging user update: {new_value}")

    try:
        memory_events.emit("user_data", {"name": "John", "age": 30})
        time.sleep(1)
        memory_events.emit("user_data", {"name": "Jane", "age": 25})
        time.sleep(1)
        memory_events.emit("user_data", {"name": "Bob", "age": 35}, ttl=2.0)
        time.sleep(3)
    finally:
        memory_events.cleanup()
```

---

## How It Works

- When you emit an event, the value is stored in shared memory.
- All registered handlers for that event are triggered in all processes using the same pool.
- TTL allows data to expire automatically, and the cleanup thread removes expired or orphaned entries.
- Thread safety is ensured via locks.
- The watcher thread in EventManager detects changes and triggers callbacks.

---

## Migration & Security Notes

- **Encryption**: To enable shared memory encryption, create a pool with `encryption_key=...` (`bytes`). Requires: `pip install cryptography`.
- **Legacy Compatibility**: All new APIs are opt-in. Existing mvent code works unchanged.
- **Performance**: Encryption/decryption introduces minor overhead on set/get, but remains fast for most IPC use cases.
- **Monitoring**: Attach `MonitoringTools` to any manager for live stats.

---

## License

MIT License

---

## Contributing

Contributions are welcome! Please submit issues or pull requests via [GitHub](https://github.com/cognition-brahmai/mvent).

---

## Authors

Developed by [BRAHMAI](https://brahmai.in)
