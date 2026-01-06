from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import BotConfig


@dataclass(slots=True)
class PollymarketClient:
    config: BotConfig

    async def _request_with_retries(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> Any:
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(self._request, method, path, body)
            except Exception as exc:  # noqa: BLE001 - bubble fatal errors after retries
                attempt += 1
                if attempt >= self.config.max_retries:
                    raise
                await asyncio.sleep(min(2**attempt, 8))

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.config.api_base_url.rstrip('/')}/{path.lstrip('/')}"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
        request = urllib.request.Request(url=url, data=data, method=method.upper())
        for key, value in self.config.headers().items():
            request.add_header(key, value)
        if data:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout) as response:  # noqa: S310 - controlled URL
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:  # noqa: PERF203 - small branching
            raise RuntimeError(f"HTTP error {exc.code} from Pollymarket: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to reach Pollymarket: {exc.reason}") from exc

    async def fetch_markets(self) -> list[dict[str, Any]]:
        return await self._request_with_retries("GET", "/markets?active=true")

    async def submit_order(self, order: dict[str, Any]) -> Any:
        if not self.config.api_key:
            raise RuntimeError("Cannot submit orders without POLLYMARKET_API_KEY")
        return await self._request_with_retries("POST", "/orders", order)
