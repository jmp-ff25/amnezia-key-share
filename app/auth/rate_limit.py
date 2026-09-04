import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    def __init__(self, limit: int = 5, window_seconds: int = 300) -> None:
        self.limit = limit
        self.window = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] < now - self.window:
                attempts.popleft()
            return len(attempts) < self.limit

    def fail(self, key: str) -> None:
        with self._lock:
            self._attempts[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_limiter = LoginRateLimiter()
