"""
Monitoring and Encryption example: Memory usage, event stats, secure pool.
"""
from mvent.core.monitoring import MonitoringTools
from mvent.core.shared_memory import SharedMemoryPool
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

def main():
    if Fernet:
        key = Fernet.generate_key()
        secure_pool = SharedMemoryPool("secure_demo_pool", encryption_key=key)
    else:
        print("Encryption demo: cryptography package not installed.")
        secure_pool = SharedMemoryPool("plain_demo_pool")

    # Monitoring demo
    monitor = MonitoringTools(pool=secure_pool)

    def handler(x):
        return x * x

    wrapped_handler = monitor.wrap_handler("square", handler)
    monitor.record_event("square_call")
    res = wrapped_handler(5)
    print("Handler result:", res)
    print("Event stats:", monitor.get_event_stats())
    print("Handler stats:", monitor.get_handler_stats())
    print("Memory stats:", monitor.get_memory_stats())

if __name__ == "__main__":
    main()