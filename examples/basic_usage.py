"""
Example usage of memory events
"""
from mvent.decorators.memory_events import MemoryEventHandler
import time

def main():
    # Create a memory event handler
    memory_events = MemoryEventHandler("example_pool")
    
    # Define an event handler
    @memory_events.on("user_data")
    def handle_user_update(new_value):
        print(f"Received user data update: {new_value}")
    
    # Define another handler for the same event
    @memory_events.on("user_data")
    def log_user_update(new_value):
        print(f"Logging user update: {new_value}")
    
    try:
        # Emit some events
        print("Emitting events...")
        memory_events.emit("user_data", {"name": "John", "age": 30})
        time.sleep(1)  # Wait for handlers to process
        
        memory_events.emit("user_data", {"name": "Jane", "age": 25})
        time.sleep(1)
        
        # Emit with TTL
        memory_events.emit("user_data", {"name": "Bob", "age": 35}, ttl=2.0)
        time.sleep(3)  # Wait for TTL to expire
        
    finally:
        memory_events.cleanup()

if __name__ == "__main__":
    main()