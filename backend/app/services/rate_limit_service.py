"""Bounded in-process rate control; distributed limits remain a deployment task."""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException

_buckets = defaultdict(deque)
_lock = Lock()


def check_rate(key, limit, window=60):
    now = monotonic()
    with _lock:
        if len(_buckets) > 2048:
            for expired in [k for k, q in _buckets.items() if not q or now - q[-1] > window]:
                _buckets.pop(expired, None)
            if len(_buckets) > 2048:
                raise HTTPException(429, 'SERVER_BUSY', headers={'Retry-After': '60'})
        queue = _buckets[key]
        while queue and now - queue[0] > window:
            queue.popleft()
        if len(queue) >= limit:
            raise HTTPException(429, 'RATE_LIMITED', headers={'Retry-After': '60'})
        queue.append(now)
