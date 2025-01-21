# mvent
by [BRAHMAI](https://brahmai.in)

A Python package that provides an event-driven interface for shared memory communication between processes.

## Features

- Shared memory communication between processes
- Event-driven architecture using decorators
- TTL support for temporary data
- Automatic cleanup of expired data
- Thread-safe operations

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