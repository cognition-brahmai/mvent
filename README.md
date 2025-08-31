# mvent
by [BRAHMAI](https://brahmai.in)

A Python package that provides an event-driven interface for shared memory communication between processes.

## Features

- Shared memory communication between processes
- Event-driven architecture using decorators
- TTL support for temporary data
- Automatic cleanup of expired data
- Thread-safe operations
- **In-memory HTTP API:** HTTP-like request/response and route handling all in RAM (no network).
- **StreamingEvent:** Publish/subscribe, chunked/real-time data streams over shared memory.
- **SocketsManager:** Pub/sub, room/channel-based, socket-like messaging—entirely RAM-backed.
- **Monitoring tools:** Live stats for pool size, event/message frequency, handler performance.
- **Optional encryption:** Secure shared memory with symmetric key (requires `cryptography`).

## Installation

```bash
pip install mvent
```

## Quick Start

```python
from mvent import MemoryEventHandler
import time

# Create a memory event handler
memory_events = MemoryEventHandler("my_pool")

# Define an event handler using decorator
@memory_events.on("user_data")
def handle_user_update(new_value):
    print(f"User data updated: {new_value}")

# Emit an event
memory_events.emit("user_data", {"name": "John", "age": 30})

# Emit with TTL (expires after 5 seconds)
memory_events.emit("user_data", {"name": "Jane"}, ttl=5.0)

# Keep the program running
time.sleep(6)
memory_events.cleanup()
```

## How It Works

The package uses memory-mapped files for shared memory communication between processes. When a process updates a value in shared memory, all registered event handlers in other processes are automatically notified and executed.

---

## Extended Usage: Advanced APIs

### InMemoryHTTPManager

```python
from mvent.core.in_memory_http import InMemoryHTTPManager
http = InMemoryHTTPManager()
@http.route("/echo")
def echo(req): return {"echo": req["data"]}
print(http.send_request("/echo", method="POST", data="hi"))
```

### StreamingEvent

```python
from mvent.core.streaming_event import StreamingEvent
stream = StreamingEvent("my_stream")
stream.subscribe(lambda d: print("Got:", d))
stream.publish("Live Message #1")
```

### SocketsManager

```python
from mvent.core.sockets_manager import SocketsManager
sm = SocketsManager()
room = "test"
sm.connect(room)
sm.subscribe(room, print)
sm.send(room, "socket message!")
```

### MonitoringTools and Encryption

```python
from mvent.core.monitoring import MonitoringTools
from mvent.core.shared_memory import SharedMemoryPool
from cryptography.fernet import Fernet
key = Fernet.generate_key()
secure_pool = SharedMemoryPool("secure_pool", encryption_key=key)
monitor = MonitoringTools(pool=secure_pool)
monitor.record_event("test")
```
- To enable encryption, install [cryptography](https://pypi.org/project/cryptography/) (`pip install cryptography`).
- All features are backward compatible.

---

## Advanced Usage

### Multiple Handlers

```python
# Multiple handlers for the same event
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
# Data expires after 60 seconds
memory_events.emit("temporary_data", "This will expire", ttl=60.0)
```

## License

MIT License