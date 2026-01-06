from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class BotConfig:
    """Configuration for the Pollymarket bot.

    Values are primarily loaded from environment variables, but defaults are
    provided so the bot can start without additional configuration for data
    scraping. Trading calls require an API key.
    """

    api_base_url: str = os.environ.get("POLLYMARKET_API_BASE", "https://clob.polymarket.com")
    api_key: str | None = os.environ.get("POLLYMARKET_API_KEY")
    poll_interval: float = float(os.environ.get("POLLYMARKET_POLL_INTERVAL", "30"))
    min_edge_bps: float = float(os.environ.get("POLLYMARKET_MIN_EDGE_BPS", "50"))
    max_orders_per_cycle: int = int(os.environ.get("POLLYMARKET_MAX_ORDERS_PER_CYCLE", "1"))
    order_size: float = float(os.environ.get("POLLYMARKET_ORDER_SIZE", "10"))
    request_timeout: float = float(os.environ.get("POLLYMARKET_REQUEST_TIMEOUT", "30"))
    max_retries: int = int(os.environ.get("POLLYMARKET_MAX_RETRIES", "3"))
    dry_run: bool = False

    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "pollybot/0.1"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
