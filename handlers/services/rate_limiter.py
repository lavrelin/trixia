# services/rate_limiter.py
class RateLimiter:
    def __init__(self):
        self.user_requests = {}
    
    async def check_rate_limit(self, user_id: int, limit: int = 10) -> bool:
        """Проверка X запросов в минуту"""
        now = datetime.now()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Удаляем старые запросы
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if (now - t).total_seconds() < 60
        ]
        
        if len(self.user_requests[user_id]) >= limit:
            return False
        
        self.user_requests[user_id].append(now)
        return True
