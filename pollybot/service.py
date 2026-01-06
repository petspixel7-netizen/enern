from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .client import PollymarketClient
from .config import BotConfig
from .strategy import MarketSignal, find_edges

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RiskState:
    trades_today: int = 0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    last_pause: datetime | None = None
    current_day: datetime | None = None
    market_last_trade: dict[str, datetime] = field(default_factory=dict)


class RiskManager:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.state = RiskState(current_day=datetime.now(UTC))

    def _reset_daily(self, now: datetime) -> None:
        if self.state.current_day is None or now.date() != self.state.current_day.date():
            self.state = RiskState(current_day=now)
            logger.info("Daily counters reset for new UTC day")

    def effective_bankroll(self) -> float:
        return max(self.config.bankroll + self.state.daily_pnl, 0.0)

    def _cooldown_active(self, now: datetime) -> bool:
        if self.state.last_pause is None:
            return False
        cooldown_until = self.state.last_pause + timedelta(hours=self.config.cooldown_hours)
        if now < cooldown_until:
            return True
        self.state.last_pause = None
        self.state.consecutive_losses = 0
        logger.info("Cooldown expired; counters reset")
        return False

    def check_can_trade(self, now: datetime) -> tuple[bool, str]:
        self._reset_daily(now)
        bankroll = self.effective_bankroll()
        if bankroll <= 0:
            return False, "No bankroll configured"
        if self._cooldown_active(now):
            return False, "Cooling down after losses"
        if self.state.trades_today >= self.config.max_trades_per_day:
            return False, "Max trades per day reached"
        loss_limit = -self.config.daily_loss_limit_pct * bankroll
        if self.state.daily_pnl <= loss_limit:
            return False, "Daily loss limit reached"
        if self.state.consecutive_losses >= self.config.max_consecutive_losses:
            if self.state.last_pause is None:
                self.state.last_pause = now
                logger.warning("Entering cooldown after %s consecutive losses", self.state.consecutive_losses)
            return False, "Max consecutive losses reached"
        return True, "OK"

    def record_trade(self, pnl_change: float, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self.state.trades_today += 1
        self.state.daily_pnl += pnl_change
        if pnl_change < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0
        if self.state.consecutive_losses >= self.config.max_consecutive_losses and self.state.last_pause is None:
            self.state.last_pause = now
            logger.warning("Entering cooldown after %s consecutive losses", self.state.consecutive_losses)

    def market_blocked(self, market_id: str, now: datetime) -> bool:
        last_trade = self.state.market_last_trade.get(market_id)
        if last_trade is None:
            return False
        return now - last_trade < timedelta(hours=self.config.market_cooldown_hours)

    def record_market_trade(self, market_id: str, now: datetime) -> None:
        self.state.market_last_trade[market_id] = now


def describe_signal(signal: MarketSignal) -> dict[str, object]:
    return {
        "marketId": signal.market_id,
        "outcome": signal.outcome,
        "size": signal.size,
        "price": signal.price,
    }


async def fetch_markets(client: PollymarketClient) -> list[dict[str, object]]:
    return await client.fetch_markets()


def _extract_prices(market: dict[str, object]) -> tuple[float | None, float | None]:
    outcomes = market.get("outcomes") or []
    yes_price = next((o.get("price") for o in outcomes if str(o.get("name", "")).lower() == "yes"), None)
    no_price = next((o.get("price") for o in outcomes if str(o.get("name", "")).lower() == "no"), None)
    return yes_price, no_price


def liquidity_and_spread_ok(market: dict[str, object]) -> tuple[bool, str]:
    liquidity = market.get("liquidity") or market.get("volume24h") or market.get("tvl")
    if liquidity is not None:
        try:
            if float(liquidity) <= 0:
                return False, "Liquidity too low"
        except (TypeError, ValueError):
            return False, "Liquidity unreadable"

    yes_price, no_price = _extract_prices(market)
    if yes_price is None or no_price is None:
        return False, "Missing bid/ask prices"
    try:
        spread = abs(float(yes_price) - float(no_price))
    except (TypeError, ValueError):
        return False, "Spread unreadable"
    if spread > 0.2:
        return False, "Spread too wide"
    return True, "OK"


async def run_bot(config: BotConfig) -> None:
    client = PollymarketClient(config)
    risk = RiskManager(config)
    logger.info("Starting Pollymarket bot with interval %.1fs", config.poll_interval)
    next_scan: datetime = datetime.now(UTC)

    async def _execute_signal(signal: MarketSignal, now: datetime) -> None:
        try:
            logger.info("Signal %s", signal.reason)
        except Exception:  # noqa: BLE001 - logging must not break execution
            pass
        risk.record_market_trade(signal.market_id, now)
        risk.record_trade(0.0, now)
        if config.dry_run:
            try:
                logger.info("Dry-run enabled, not sending order: %s", describe_signal(signal))
            except Exception:  # noqa: BLE001 - logging must not break execution
                pass
            return
        try:
            order = await client.submit_order(describe_signal(signal))
            logger.info("Submitted order %s", order)
        except Exception:  # noqa: BLE001 - log all failures for visibility
            logger.exception("Failed to submit order")
    try:
        while True:
            now = datetime.now(UTC)
            try:
                if config.hourly_scan and now < next_scan:
                    await asyncio.sleep(config.poll_interval)
                    continue

                markets = await fetch_markets(client)
                logger.info("Fetched %s markets for scan", len(markets))
                order_size = config.calc_order_size(risk.effective_bankroll())
                signals = find_edges(
                    markets,
                    min_edge_bps=config.min_edge_bps,
                    max_orders=config.max_orders_per_cycle,
                    order_size=order_size,
                )
                market_by_id = {str(market.get("id")): market for market in markets}

                if not signals:
                    logger.info("HOURLY SCAN - NO TRADE: %s", "No edges above threshold")
                else:
                    for signal in signals:
                        market = market_by_id.get(signal.market_id, {})
                        ok_market, market_reason = liquidity_and_spread_ok(market)
                        if not ok_market:
                            logger.info("HOURLY SCAN - NO TRADE: %s", market_reason)
                            continue
                        can_trade, reason = risk.check_can_trade(now)
                        if signal.size <= 0:
                            logger.info("HOURLY SCAN - NO TRADE: order size is zero")
                            continue
                        if not can_trade:
                            logger.info("HOURLY SCAN - NO TRADE: %s", reason)
                            continue
                        if risk.market_blocked(signal.market_id, now):
                            logger.info(
                                "HOURLY SCAN - NO TRADE: market %s in cooldown",
                                signal.market_id,
                            )
                            continue

                        await _execute_signal(signal, now)

                next_scan = now + timedelta(hours=1) if config.hourly_scan else now + timedelta(seconds=config.poll_interval)

            except Exception:  # noqa: BLE001 - log unexpected failures per cycle
                logger.exception("Cycle failed; will retry after backoff")
            await asyncio.sleep(config.poll_interval)
    except asyncio.CancelledError:
        logger.info("Bot cancelled, shutting down")
        raise
