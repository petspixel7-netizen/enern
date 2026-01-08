from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from bot.config import BotConfig
from bot.logger import log_event
from bot.types import OrderRequest, OrderResult

logger = logging.getLogger(__name__)


class ExecutionAdapter:
    async def place_order(self, order: OrderRequest) -> OrderResult:
        raise NotImplementedError

    async def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    async def fetch_order(self, order_id: str) -> OrderResult:
        raise NotImplementedError


class PolymarketExecutionAdapter(ExecutionAdapter):
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self.api_key = os.getenv("POLYMARKET_API_KEY", "")
        self.api_secret = os.getenv("POLYMARKET_API_SECRET", "")

    async def place_order(self, order: OrderRequest) -> OrderResult:
        if self.config.dry_run:
            return self._simulate_fill(order)
        payload = {
            "market": self.config.market,
            "side": order.side,
            "price": order.price,
            "size": order.size,
            "time_in_force": "GTC",
            "client_order_id": order.client_order_id,
        }
        response = await self._request("POST", self.config.execution.order_path, json=payload)
        order_id = response.get("id") or response.get("order_id") or order.client_order_id
        return OrderResult(
            order_id=str(order_id),
            filled_size=0.0,
            avg_price=0.0,
            status="open",
            remaining_size=order.size,
        )

    async def cancel_order(self, order_id: str) -> None:
        if self.config.dry_run:
            return
        path = self.config.execution.cancel_path.format(order_id=order_id)
        await self._request("DELETE", path)

    async def fetch_order(self, order_id: str) -> OrderResult:
        if self.config.dry_run:
            return OrderResult(
                order_id=order_id,
                filled_size=0.0,
                avg_price=0.0,
                status="filled",
                remaining_size=0.0,
            )
        path = self.config.execution.order_status_path.format(order_id=order_id)
        response = await self._request("GET", path)
        return OrderResult(
            order_id=str(response.get("id", order_id)),
            filled_size=float(response.get("filled_size", 0.0)),
            avg_price=float(response.get("avg_price", 0.0)),
            status=str(response.get("status", "open")),
            remaining_size=float(response.get("remaining_size", 0.0)),
        )

    async def _request(self, method: str, path: str, json: Optional[dict] = None) -> dict:
        if not self._session:
            self._session = aiohttp.ClientSession()
        url = f"{self.config.execution.rest_url}{path}"
        headers = {}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        if self.api_secret:
            headers["X-API-SECRET"] = self.api_secret
        async with self._session.request(
            method, url, json=json, headers=headers, timeout=self.config.execution.request_timeout_seconds
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _simulate_fill(self, order: OrderRequest) -> OrderResult:
        log_event(logger, "DRY_RUN_ORDER", **asdict(order))
        return OrderResult(
            order_id=f"dry-{uuid.uuid4()}",
            filled_size=order.size,
            avg_price=order.price,
            status="filled",
            remaining_size=0.0,
        )

    async def close(self) -> None:
        if self._session:
            await self._session.close()


class ExecutionEngine:
    def __init__(self, config: BotConfig, adapter: ExecutionAdapter) -> None:
        self.config = config
        self.adapter = adapter

    async def execute_limit_gtc(self, order: OrderRequest) -> OrderResult:
        result = await self.adapter.place_order(order)
        if result.status == "filled":
            return result

        ttl = self.config.execution.order_ttl_seconds
        await asyncio.sleep(ttl)
        refreshed = await self.adapter.fetch_order(result.order_id)
        if refreshed.status == "filled":
            return refreshed

        await self.adapter.cancel_order(result.order_id)
        if self.config.execution.max_requotes <= 0:
            return refreshed
        return refreshed


def generate_client_order_id(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:8]}"
