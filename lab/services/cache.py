import time
class TTLCache:
    def __init__(self,ttl=60):self.ttl=ttl;self.data={}
    def get(self,key,loader):
        now=time.monotonic()
        if key not in self.data or self.data[key][0]<=now:
            self.data[key]=(now+self.ttl,loader())
        return self.data[key][1]
    def invalidate(self,key):self.data.pop(key,None)
