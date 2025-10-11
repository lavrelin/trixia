# services/cache_service.py
class CacheService:
    def __init__(self, ttl: int = 300):
        self._cache = {}
        self.ttl = ttl
    
    async def get(self, key: str):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return value
        return None
    
    async def set(self, key: str, value):
        self._cache[key] = (value, datetime.now())
