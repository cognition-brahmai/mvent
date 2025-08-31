# shared_memory_pool.py  
import pickle  
import mmap  
import os  
import threading  
import time  
import weakref  
import tempfile  
import signal  
import atexit  
from typing import Any, Dict, Optional, Set  
from dataclasses import dataclass  
from datetime import datetime  
import contextlib  
import struct  
  
@dataclass  
class MemoryEntry:  
    """Data structure for storing value metadata"""  
    value: Any  
    timestamp: float  
    ttl: Optional[float] = None  
    creator_pid: int = os.getpid()  
  
class SharedMemoryPool:  
    """  
    Shared memory pool implementation with features like TTL,   
    automatic cleanup, compression, and better error handling.  
    """  
    _instances: Set[weakref.ref] = set()  
      
    def __init__(
        self,
        pool_name: str = "default_pool",
        max_size: int = 1024 * 1024 * 10,  # 10MB default
        auto_cleanup: bool = True,
        cleanup_interval: int = 60,  # seconds
        compression: bool = True,
        temp_dir: Optional[str] = None,
        encryption_key: Optional[bytes] = None
    ):
        self.pool_name = pool_name  # Removed UUID addition
        self.max_size = max_size
        self.compression = compression
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval = cleanup_interval

        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.filename = os.path.join(self.temp_dir, f".{self.pool_name}_shared_memory.mmap")

        self.encryption_key = encryption_key
        self._lock = threading.Lock()
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()

        self._create_memory_file()

        if auto_cleanup:
            self._start_cleanup_thread()

        self._instances.add(weakref.ref(self))
  
    @contextlib.contextmanager  
    def _get_mmap(self):  
        """Context manager for handling memory-mapped file operations"""  
        with open(self.filename, "r+b") as f:  
            with mmap.mmap(f.fileno(), self.max_size) as mm:  
                yield mm  
  
    def _create_memory_file(self):  
        """Initialize the memory-mapped file with proper permissions"""  
        if not os.path.exists(self.filename):  
            with open(self.filename, "wb") as f:  
                f.write(b'\x00' * self.max_size)  
            os.chmod(self.filename, 0o600)  
  
    def _load_data(self) -> Dict[str, MemoryEntry]:
        """Load data from shared memory, optionally decrypting"""
        with self._get_mmap() as mm:
            try:
                mm.seek(0)
                header = mm.read(4)
                if not header.strip(b'\x00'):
                    return {}
                data_length = struct.unpack('I', header)[0]
                if data_length == 0 or data_length > self.max_size - 4:
                    return {}
                serialized = mm.read(data_length)
                if self.encryption_key:
                    serialized = self._decrypt_data(serialized)
                data = pickle.loads(serialized)
                if not isinstance(data, dict):
                    return {}
                return data
            except (pickle.UnpicklingError, EOFError, struct.error):
                return {}
      
    def _save_data(self, data: Dict[str, MemoryEntry]):
        """Save data to shared memory, optionally encrypted"""
        with self._get_mmap() as mm:
            serialized = pickle.dumps(data)
            if self.encryption_key:
                serialized = self._encrypt_data(serialized)
            data_length = len(serialized)
            header = struct.pack('I', data_length)  # unsigned int (4 bytes)
            total_size = len(header) + data_length
            if total_size > self.max_size:
                raise ValueError(f"Data exceeds maximum size of {self.max_size} bytes")
            mm.seek(0)
            mm.write(header)
            mm.write(serialized)
            mm.flush()
  
    def _start_cleanup_thread(self):  
        """Start the background cleanup thread"""  
        self._cleanup_thread = threading.Thread(  
            target=self._cleanup_loop,  
            daemon=True,  
            name=f"cleanup_{self.pool_name}"  
        )  
        self._cleanup_thread.start()  
  
    def _cleanup_loop(self):  
        """Background thread for automatic cleanup"""  
        while not self._stop_cleanup.is_set():  
            self._cleanup_expired()  
            self._stop_cleanup.wait(self.cleanup_interval)  
  
    def _cleanup_expired(self):  
        """Remove expired entries and perform maintenance"""  
        with self._lock:  
            try:  
                data = self._load_data()  
                current_time = time.time()  
                expired = []  
  
                for key, entry in data.items():  
                    if (entry.ttl and current_time - entry.timestamp > entry.ttl) or (not os.path.exists(f"/proc/{entry.creator_pid}")):
                        expired.append(key)  
  
                for key in expired:  
                    del data[key]  
  
                if expired:  
                    self._save_data(data)  
            except Exception as e:  
                print(f"Error during cleanup: {e}")  
  
    def set(  
        self,   
        name: str,   
        value: Any,   
        ttl: Optional[float] = None,  
        raise_on_error: bool = True  
    ) -> bool:  
        """Set a value in the shared memory pool"""  
        try:  
            with self._lock:  
                data = self._load_data()  
                entry = MemoryEntry(  
                    value=value,  
                    timestamp=time.time(),  
                    ttl=ttl,  
                    creator_pid=os.getpid()  
                )  
                data[name] = entry  
                self._save_data(data)  
            return True  
        except Exception as e:  
            if raise_on_error:  
                raise  
            return False  
  
    def get(  
        self,   
        name: str,   
        default: Any = None,  
        with_metadata: bool = False  
    ) -> Any:  
        """Get a value from the shared memory pool"""  
        with self._lock:  
            data = self._load_data()  
            entry = data.get(name)  
              
            if entry is None:  
                return default  
              
            if entry.ttl and time.time() - entry.timestamp > entry.ttl:  
                del data[name]  
                self._save_data(data)  
                return default  
              
            return (entry.value, entry) if with_metadata else entry.value  
  
    def delete(self, name: str) -> bool:  
        """Delete a value from the shared memory pool"""  
        with self._lock:  
            data = self._load_data()  
            if name in data:  
                del data[name]  
                self._save_data(data)  
                return True  
            return False  
  
    def clear(self) -> None:  
        """Clear all data from the shared memory pool"""  
        with self._lock:  
            self._save_data({})  
  
    def get_all(self) -> Dict[str, Any]:  
        """Get all key-value pairs from the shared memory pool"""  
        with self._lock:  
            data = self._load_data()  
            return {k: v.value for k, v in data.items()}  
  
    def get_stats(self) -> Dict[str, Any]:  
        """Get statistics about the memory pool"""  
        with self._lock:  
            data = self._load_data()  
            total_size = os.path.getsize(self.filename)  
            used_size = len(pickle.dumps(data))  
              
            return {  
                "total_size": total_size,  
                "used_size": used_size,  
                "free_size": total_size - used_size,  
                "num_entries": len(data),  
                "creation_time": datetime.fromtimestamp(  
                    os.path.getctime(self.filename)  
                ).isoformat(),  
                "last_modified": datetime.fromtimestamp(  
                    os.path.getmtime(self.filename)  
                ).isoformat()  
            }  
  
    def cleanup(self):  
        """Perform cleanup when shutting down"""  
        if self._cleanup_thread and self._cleanup_thread.is_alive():  
            self._stop_cleanup.set()  
            self._cleanup_thread.join(timeout=1.0)  
        # Do not remove the shared memory file  
        # File remains for other processes  
        # If needed, user can call a method to delete the file explicitly  
  
    def __enter__(self):  
        """Context manager support"""  
        return self  
  
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context manager exit"""
        self.cleanup()

    # --- Encryption Support ---
    def _encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypts bytes using the provided encryption_key (Fernet).
        Requires: pip install cryptography
        """
        if not self.encryption_key:
            return data
        try:
            from cryptography.fernet import Fernet
            cipher = Fernet(self.encryption_key)
            return cipher.encrypt(data)
        except ImportError:
            raise ImportError("cryptography package is required for encryption. Install with 'pip install cryptography'")
        except Exception:
            return data

    def _decrypt_data(self, data: bytes) -> bytes:
        """
        Decrypts bytes using the provided encryption_key.
        """
        if not self.encryption_key:
            return data
        try:
            from cryptography.fernet import Fernet
            cipher = Fernet(self.encryption_key)
            return cipher.decrypt(data)
        except Exception:
            return data