"""Local TTL cache: per-process, read-only copy, explicit invalidation on writes."""
import time

class VehicleReadCache:
    def __init__(self, ttl_seconds=30.0, clock=None):
        self.ttl_seconds = ttl_seconds
        self.clock = clock or time.monotonic
        self.entries = {}
        self.hits=0
        self.misses=0

    def get(self, key, loader):
        entry=self.entries.get(key)
        now=self.clock()
        if entry is not None and now < entry[0]:
            self.hits+=1
            return entry[1]
        self.misses+=1
        value=loader(key)
        if value is not None:
            self.entries[key]=(now+self.ttl_seconds,value)
        return value

    def invalidate(self, key):
        self.entries.pop(key, None)

    def stats(self):
        return {'hits':self.hits,'misses':self.misses,'ttl_seconds':self.ttl_seconds,'entries':len(self.entries)}
