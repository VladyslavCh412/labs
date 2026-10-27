"""Bounded, single-flight page cache local to one Trips process."""
from threading import Lock
import time


class TripPageCache:
    def __init__(self, ttl=1.0, capacity=128, clock=time.monotonic):
        self.ttl, self.capacity, self.clock = ttl, capacity, clock
        self._entries = {}
        self._lock = Lock()

    def get(self, key, loader):
        # Loading under the same lock prevents an expiry stampede. The loader
        # performs a bounded 50/100-row SQLite read, never a remote HTTP call.
        with self._lock:
            now = self.clock()
            entry = self._entries.get(key)
            if entry is not None and now < entry[0]:
                return entry[1]
            value = loader()
            if key not in self._entries and len(self._entries) >= self.capacity:
                self._entries.pop(next(iter(self._entries)))
            self._entries[key] = (self.clock() + self.ttl, value)
            return value

    def invalidate(self):
        with self._lock:
            self._entries.clear()
