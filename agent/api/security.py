"""HTTP authentication and bounded admission for costly web operations.

IAM Lambda invocations and offline workers do not enter this HTTP boundary.
The shared API credential has one per-process budget; deployments with multiple
workers must also enforce an aggregate quota at their gateway.
"""

from collections import deque
from collections.abc import Callable
import hmac
import os
from threading import Lock
import time

from fastapi import Depends, HTTPException, Query, Request
from starlette.types import ASGIApp, Receive, Scope, Send

from config.settings import settings


class RequestSizeLimitMiddleware:
    """Count streamed bytes before JSON decoding, including chunked requests."""

    def __init__(self, app: ASGIApp, max_bytes: int = 2 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                raise HTTPException(status_code=413, detail="Request body exceeds the server limit")
            return message

        await self.app(scope, bounded_receive, send)


def require_api_key(request: Request) -> None:
    expected = os.getenv("API_KEY", settings.api_key)
    provided = request.headers.get("X-API-Key", "")
    if not expected or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="API authentication required")


class WorkBudget:
    """Shared-key rate and concurrency limits, safe across request event loops."""

    def __init__(
        self,
        max_calls: int = 10,
        max_active: int = 2,
        window_seconds: float = 60,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_calls = max_calls
        self.max_active = max_active
        self.window_seconds = window_seconds
        self.clock = clock
        self.calls: deque[float] = deque()
        self.active = 0
        self.lock = Lock()

    def acquire(self) -> None:
        with self.lock:
            now = self.clock()
            while self.calls and self.calls[0] <= now - self.window_seconds:
                self.calls.popleft()
            if len(self.calls) >= self.max_calls or self.active >= self.max_active:
                raise HTTPException(
                    status_code=429, detail="Work budget exhausted", headers={"Retry-After": "60"}
                )
            self.calls.append(now)
            self.active += 1

    def release(self) -> None:
        with self.lock:
            self.active -= 1


work_budget = WorkBudget()


async def require_work_budget(_authenticated: None = Depends(require_api_key)):
    budget = work_budget
    budget.acquire()
    try:
        yield
    finally:
        budget.release()


async def require_deep_health_access(request: Request, deep: bool = Query(default=False)):
    if deep:
        require_api_key(request)
        budget = work_budget
        budget.acquire()
        try:
            yield
        finally:
            budget.release()
    else:
        yield
