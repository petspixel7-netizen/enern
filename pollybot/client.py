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
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - controlled URL
            return json.loads(response.read().decode())

    async def fetch_markets(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._request, "GET", "/markets?active=true")

    async def submit_order(self, order: dict[str, Any]) -> Any:
        if not self.config.api_key:
            raise RuntimeError("Cannot submit orders without POLLYMARKET_API_KEY")
        return await asyncio.to_thread(self._request, "POST", "/orders", order)
