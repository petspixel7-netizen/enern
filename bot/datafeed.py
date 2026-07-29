from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Deque, Dict, Optional, Tuple

import aiohttp
import websockets

from bot.config import BotConfig
from bot.types import Quote, SignalEvent

logger = logging.getLogger(__name__)


@dataclass
class RollingWindow:
    samples: Deque[Tuple[datetime, float]]
    window_seconds: int

    def add(self, timestamp: datetime, price: float) -> None:
        self.samples.append((timestamp, price))
        cutoff = timestamp.timestamp() - self.window_seconds
        while self.samples and self.samples[0][0].timestamp() < cutoff:
            self.samples.popleft()

    def movement_pct(self) -> Optional[float]:
        if len(self.samples) < 2:
            return None
        oldest_price = self.samples[0][1]
        newest_price = self.samples[-1][1]
        if oldest_price == 0:
            return None
        return ((newest_price - oldest_price) / oldest_price) * 100.0


class DatafeedAdapter:
    async def stream(self) -> AsyncIterator[Quote]:
        raise NotImplementedError


class PolymarketDatafeed(DatafeedAdapter):
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._stop = asyncio.Event()

    async def stream(self) -> AsyncIterator[Quote]:
        if self.config.datafeed.mode == "websocket":
            async for quote in self._stream_websocket():
                yield quote
        else:
            async for quote in self._stream_polling():
                yield quote

    async def _stream_websocket(self) -> AsyncIterator[Quote]:
        """
        This is a lightweight adapter; plug the official Polymarket CLOB websocket
        subscription payloads here.
        """
        ws_url = self.config.datafeed.ws_url
        market = self.config.market
        logger.info("Connecting websocket %s for market %s", ws_url, market)
        async for quote in self._ws_loop(ws_url, market):
            yield quote

    async def _ws_loop(self, ws_url: str, market: str) -> AsyncIterator[Quote]:
        async with websockets.connect(ws_url, ping_interval=20) as websocket:
            subscribe_payload = {
                "type": "subscribe",
                "channel": "orderbook",
                "market": market,
            }
            await websocket.send(json_dumps(subscribe_payload))
            async for message in websocket:
                payload = json_loads(message)
                quote = parse_orderbook_payload(payload)
                if quote:
                    yield quote

    async def _stream_polling(self) -> AsyncIterator[Quote]:
        if not self._session:
            self._session = aiohttp.ClientSession()
        backoff = self.config.datafeed.poll_interval_seconds
        while not self._stop.is_set():
            try:
                quote = await self._fetch_orderbook()
                if quote:
                    yield quote
                await asyncio.sleep(self.config.datafeed.poll_interval_seconds)
                backoff = self.config.datafeed.poll_interval_seconds
            except Exception as exc:  # noqa: BLE001 - explicit circuit breaker handles errors
                logger.warning("Polling error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config.datafeed.backoff_max_seconds)

    async def _fetch_orderbook(self) -> Optional[Quote]:
        if not self._session:
            self._session = aiohttp.ClientSession()
        url = f"{self.config.datafeed.rest_url}{self.config.datafeed.orderbook_path}"
        params = {"market": self.config.market}
        async with self._session.get(url, params=params, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return parse_orderbook_payload(data)

    async def close(self) -> None:
        self._stop.set()
        if self._session:
            await self._session.close()


def parse_orderbook_payload(payload: Dict[str, object]) -> Optional[Quote]:
    """
    Expected payload format (adapt as needed):
    {
      "side": "UP",
      "best_bid": 0.48,
      "best_ask": 0.52,
      "liquidity": 1200.0
    }
    """
    try:
        side = str(payload["side"]).upper()
        best_bid = float(payload["best_bid"])
        best_ask = float(payload["best_ask"])
        liquidity = float(payload.get("liquidity", 0.0))
        spread = max(best_ask - best_bid, 0.0)
        return Quote(
            side=side,
            best_bid=best_bid,
            best_ask=best_ask,
            liquidity=liquidity,
            spread=spread,
            timestamp=datetime.now(timezone.utc),
        )
    except (KeyError, TypeError, ValueError):
        return None


def json_dumps(payload: Dict[str, object]) -> str:
    import json

    return json.dumps(payload)


def json_loads(message: str) -> Dict[str, object]:
    import json

    return json.loads(message)


class MovementDetector:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.windows: Dict[str, RollingWindow] = {}

    def update(self, quote: Quote) -> Optional[SignalEvent]:
        window = self.windows.setdefault(
            quote.side,
            RollingWindow(deque(), self.config.strategy.move_window_seconds),
        )
        window.add(quote.timestamp, quote.best_ask)
        move_pct = window.movement_pct()
        if move_pct is None:
            return None
        threshold = self.config.strategy.move_pct_threshold
        if self.config.strategy.trigger_mode == "dump" and move_pct <= -threshold:
            return SignalEvent(
                timestamp=quote.timestamp,
                side=quote.side,
                entry_price=quote.best_ask,
                move_pct=move_pct,
                spread=quote.spread,
                liquidity=quote.liquidity,
            )
        if self.config.strategy.trigger_mode == "pump" and move_pct >= threshold:
            return SignalEvent(
                timestamp=quote.timestamp,
                side=quote.side,
                entry_price=quote.best_ask,
                move_pct=move_pct,
                spread=quote.spread,
                liquidity=quote.liquidity,
            )
        return None
