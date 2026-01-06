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
    request_timeout: float = float(os.environ.get("POLLYMARKET_REQUEST_TIMEOUT", "30"))
    max_retries: int = int(os.environ.get("POLLYMARKET_MAX_RETRIES", "3"))

    bankroll: float = float(os.environ.get("POLLYBOT_BANKROLL", os.environ.get("BANKROLL", "1000")))
    risk_per_trade_pct: float = float(os.environ.get("RISK_PER_TRADE_PCT", "0.005"))
    max_trades_per_day: int = int(os.environ.get("MAX_TRADES_PER_DAY", "10"))
    daily_loss_limit_pct: float = float(os.environ.get("DAILY_LOSS_LIMIT_PCT", "0.02"))
    max_consecutive_losses: int = int(os.environ.get("MAX_CONSECUTIVE_LOSSES", "3"))
    cooldown_hours: int = int(os.environ.get("COOLDOWN_HOURS", "24"))
    hourly_scan: bool = os.environ.get("HOURLY_SCAN", "false").lower() == "true"
    market_cooldown_hours: int = int(os.environ.get("MARKET_COOLDOWN_HOURS", "3"))
    dry_run: bool = False

    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "pollybot/0.1"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def calc_order_size(self, effective_bankroll: float | None = None) -> float:
        """Compute dynamic order size based on bankroll and risk percent.

        Fixed sizing is intentionally disallowed to keep risk proportional to
        bankroll across all trades.
        """

        bankroll = effective_bankroll if effective_bankroll is not None else self.bankroll
        if bankroll <= 0:
            return 0.0
        return bankroll * self.risk_per_trade_pct
