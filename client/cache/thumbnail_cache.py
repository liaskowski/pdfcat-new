"""
High-performance thumbnail caching system with LRU eviction and memory limits
"""

import os
import hashlib
import threading
from typing import Optional, Dict, Tuple
from pathlib import Path
from collections import OrderedDict
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap
import time

class ThumbnailCache(QObject):
    """
    Thread-safe LRU cache for thumbnails with memory management
    """
    
    cache_hit = pyqtSignal(int)  # document_id
    cache_miss = pyqtSignal(int)  # document_id
    memory_warning = pyqtSignal(str)  # warning message
    
    def __init__(self, max_memory_mb: int = 100, max_items: int = 1000):
        super().__init__()
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_items = max_items
        
        # LRU cache using OrderedDict (preserves insertion order)
        self._cache: OrderedDict[int, Tuple[QPixmap, int, float]] = OrderedDict()
        self._current_memory = 0
        self._lock = threading.RLock()
        
        # Cache statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        print(f"🖼️  ThumbnailCache initialized: {max_memory_mb}MB, {max_items} items")
    
    def _generate_cache_key(self, document_id: int, size: Tuple[int, int]) -> str:
        """Generate unique cache key for thumbnail"""
        key_data = f"{document_id}_{size[0]}x{size[1]}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """Estimate memory usage of pixmap in bytes"""
        # Rough estimation: width * height * 4 bytes (RGBA)
        return pixmap.width() * pixmap.height() * 4
    
    def _evict_if_needed(self, new_item_size: int):
        """Evict items if cache is full or memory limit exceeded"""
        while (len(self._cache) >= self.max_items or 
               self._current_memory + new_item_size > self.max_memory_bytes):
            
            if not self._cache:
                break
            
            # Remove oldest item (LRU)
            oldest_id, (oldest_pixmap, oldest_size, oldest_time) = self._cache.popitem(last=False)
            self._current_memory -= oldest_size
            self._evictions += 1
            
            print(f"🗑️  Evicted thumbnail {oldest_id} (freed {oldest_size/1024:.1f}KB)")
    
    def get(self, document_id: int, size: Tuple[int, int] = (200, 200)) -> Optional[QPixmap]:
        """Get thumbnail from cache"""
        with self._lock:
            cache_key = self._generate_cache_key(document_id, size)
            
            if document_id in self._cache:
                # Move to end (mark as recently used)
                pixmap, pixmap_size, timestamp = self._cache.pop(document_id)
                self._cache[document_id] = (pixmap, pixmap_size, time.time())
                self._hits += 1
                self.cache_hit.emit(document_id)
                return pixmap.copy()  # Return copy to prevent modification
            else:
                self._misses += 1
                self.cache_miss.emit(document_id)
                return None
    
    def put(self, document_id: int, pixmap: QPixmap, size: Tuple[int, int] = (200, 200)):
        """Put thumbnail into cache"""
        if pixmap.isNull():
            return
        
        with self._lock:
            pixmap_size = self._estimate_pixmap_size(pixmap)
            current_time = time.time()
            
            # Remove existing entry if present
            if document_id in self._cache:
                _, old_size, _ = self._cache.pop(document_id)
                self._current_memory -= old_size
            
            # Evict if needed
            self._evict_if_needed(pixmap_size)
            
            # Add new entry
            self._cache[document_id] = (pixmap.copy(), pixmap_size, current_time)
            self._current_memory += pixmap_size
            
            print(f"💾 Cached thumbnail {document_id} ({pixmap_size/1024:.1f}KB)")
    
    def remove(self, document_id: int):
        """Remove specific thumbnail from cache"""
        with self._lock:
            if document_id in self._cache:
                _, pixmap_size, _ = self._cache.pop(document_id)
                self._current_memory -= pixmap_size
                print(f"🗑️  Removed thumbnail {document_id} from cache")
    
    def clear(self):
        """Clear all cached thumbnails"""
        with self._lock:
            cleared_count = len(self._cache)
            cleared_memory = self._current_memory
            self._cache.clear()
            self._current_memory = 0
            print(f"🧹 Cleared {cleared_count} thumbnails ({cleared_memory/1024/1024:.1f}MB)")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'items': len(self._cache),
                'memory_mb': self._current_memory / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_percent': hit_rate,
                'evictions': self._evictions,
                'memory_usage_percent': (self._current_memory / self.max_memory_bytes * 100)
            }
    
    def cleanup_old_thumbnails(self, max_age_hours: int = 24):
        """Remove thumbnails older than specified age"""
        with self._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            old_items = []
            for doc_id, (_, _, timestamp) in self._cache.items():
                if current_time - timestamp > max_age_seconds:
                    old_items.append(doc_id)
            
            for doc_id in old_items:
                self.remove(doc_id)
            
            if old_items:
                print(f"🧹 Cleaned up {len(old_items)} old thumbnails")

# Global cache instance
_thumbnail_cache: Optional[ThumbnailCache] = None

def get_thumbnail_cache() -> ThumbnailCache:
    """Get global thumbnail cache instance"""
    global _thumbnail_cache
    if _thumbnail_cache is None:
        _thumbnail_cache = ThumbnailCache(max_memory_mb=100, max_items=1000)
    return _thumbnail_cache

def clear_thumbnail_cache():
    """Clear global thumbnail cache"""
    global _thumbnail_cache
    if _thumbnail_cache:
        _thumbnail_cache.clear()
        _thumbnail_cache = None

# Usage example:
# cache = get_thumbnail_cache()
# thumbnail = cache.get(document_id)
# if thumbnail is None:
#     # Generate thumbnail
#     thumbnail = generate_thumbnail(...)
#     cache.put(document_id, thumbnail)
