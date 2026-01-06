from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from .client import PollymarketClient
from .config import BotConfig
from .strategy import MarketSignal, find_edges

logger = logging.getLogger(__name__)


def describe_signal(signal: MarketSignal) -> dict[str, object]:
    return {
        "marketId": signal.market_id,
        "outcome": signal.outcome,
        "size": signal.size,
        "price": signal.price,
    }


async def process_cycle(client: PollymarketClient, config: BotConfig) -> None:
    markets = await client.fetch_markets()
    signals = find_edges(markets, min_edge_bps=config.min_edge_bps, max_orders=config.max_orders_per_cycle)
    if not signals:
        logger.info("No signals this cycle")
        return

    for signal in signals:
        logger.info("Signal %s", signal.reason)
        if config.dry_run:
            logger.info("Dry-run enabled, not sending order: %s", describe_signal(signal))
            continue
        try:
            order = await client.submit_order(describe_signal(signal))
            logger.info("Submitted order %s", order)
        except Exception as exc:  # noqa: BLE001 - log all failures for visibility
            logger.exception("Failed to submit order: %s", exc)


async def run_bot(config: BotConfig) -> None:
    client = PollymarketClient(config)
    logger.info("Starting Pollymarket bot with interval %.1fs", config.poll_interval)
    while True:
        await process_cycle(client, config)
        await asyncio.sleep(config.poll_interval)
