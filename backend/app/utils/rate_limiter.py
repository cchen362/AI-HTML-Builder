from collections import defaultdict
import time


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        self.requests[key] = [
            t for t in self.requests[key] if now - t < self.window
        ]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        self.requests[key] = [
            t for t in self.requests[key] if now - t < self.window
        ]
        return max(0, self.max_requests - len(self.requests[key]))
