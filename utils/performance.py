"""
Performance optimization utilities for LanShare.
"""

import os
import threading
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib


class PerformanceCache:
    """Thread-safe cache with TTL support for performance optimization."""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires'] > time.time():
                    entry['hits'] += 1
                    return entry['value']
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl,
                'hits': 0,
                'created': time.time()
            }
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(entry['hits'] for entry in self._cache.values())
            return {
                'entries': len(self._cache),
                'total_hits': total_hits,
                'memory_usage': sum(len(str(entry['value'])) for entry in self._cache.values())
            }


def cache_result(ttl: int = 300):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        cache = PerformanceCache(ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function args
            key = hashlib.md5(str((args, kwargs)).encode()).hexdigest()
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        
        wrapper.cache = cache
        return wrapper
    return decorator


class FileSystemOptimizer:
    """Utilities for optimizing file system operations."""
    
    @staticmethod
    def get_optimal_chunk_size(file_size: int) -> int:
        """Calculate optimal chunk size based on file size."""
        if file_size < 1024 * 1024:  # < 1MB
            return 64 * 1024  # 64KB
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return 1024 * 1024  # 1MB
        else:
            return 4 * 1024 * 1024  # 4MB
    
    @staticmethod
    def should_use_mmap(file_size: int) -> bool:
        """Determine if memory mapping should be used for a file."""
        # Use mmap for files larger than 50MB but smaller than available RAM/4
        min_size = 50 * 1024 * 1024
        try:
            import psutil
            max_size = psutil.virtual_memory().available // 4
            return min_size <= file_size <= max_size
        except ImportError:
            # Fallback if psutil not available
            return file_size >= min_size
    
    @staticmethod
    def get_thread_count() -> int:
        """Get optimal thread count for parallel operations."""
        cpu_count = os.cpu_count() or 1
        return min(32, cpu_count * 2)  # Cap at 32 threads


class TransferOptimizer:
    """Utilities for optimizing network transfers."""
    
    @staticmethod
    def calculate_optimal_parallel_downloads(total_files: int, total_size: int) -> int:
        """Calculate optimal number of parallel downloads."""
        if total_files <= 2:
            return 1
        elif total_files <= 10:
            return min(4, total_files)
        elif total_size > 1024 * 1024 * 1024:  # > 1GB
            return 2  # Fewer connections for large transfers
        else:
            return min(8, total_files // 2)
    
    @staticmethod
    def should_compress_response(content_size: int, content_type: str = 'application/json') -> bool:
        """Determine if response should be compressed."""
        # Compress if size > 1KB and content type is compressible
        compressible_types = {
            'application/json',
            'text/',
            'application/xml'
        }
        
        if content_size < 1024:
            return False
            
        return any(content_type.startswith(t) for t in compressible_types)


class MemoryOptimizer:
    """Utilities for optimizing memory usage."""
    
    @staticmethod
    def get_available_memory() -> int:
        """Get available memory in bytes."""
        try:
            import psutil
            return psutil.virtual_memory().available
        except ImportError:
            # Fallback: assume 1GB available
            return 1024 * 1024 * 1024
    
    @staticmethod
    def should_stream_file(file_size: int) -> bool:
        """Determine if file should be streamed rather than loaded into memory."""
        available_memory = MemoryOptimizer.get_available_memory()
        # Stream if file is larger than 10% of available memory
        return file_size > (available_memory * 0.1)
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str, max_age_hours: int = 1) -> None:
        """Clean up temporary files older than specified age."""
        import glob
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for temp_file in glob.glob(os.path.join(temp_dir, "*")):
            try:
                if os.path.isfile(temp_file):
                    file_age = current_time - os.path.getctime(temp_file)
                    if file_age > max_age_seconds:
                        os.remove(temp_file)
            except (OSError, IOError):
                continue


# Global instances
global_cache = PerformanceCache()
fs_optimizer = FileSystemOptimizer()
transfer_optimizer = TransferOptimizer()
memory_optimizer = MemoryOptimizer()