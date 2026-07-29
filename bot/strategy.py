from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from bot.config import BotConfig
from bot.execution import ExecutionEngine, generate_client_order_id
from bot.logger import Journal, log_event
from bot.risk import RiskManager
from bot.types import OrderRequest, PositionState, Quote, SignalEvent

logger = logging.getLogger(__name__)


class DipHedgeStrategy:
    def __init__(
        self,
        config: BotConfig,
        execution: ExecutionEngine,
        risk: RiskManager,
        journal: Journal,
    ) -> None:
        self.config = config
        self.execution = execution
        self.risk = risk
        self.journal = journal
        self.position: Optional[PositionState] = None
        self.latest_quotes: Dict[str, Quote] = {}

    async def on_quote(self, quote: Quote) -> None:
        self.latest_quotes[quote.side] = quote
        if self.position:
            await self._evaluate_leg2(quote.timestamp)

    async def on_signal(self, signal: SignalEvent) -> None:
        log_event(logger, "SIGNAL", **asdict(signal))
        if not self.risk.can_trade():
            return
        if self.position:
            return
        await self._enter_leg1(signal)

    async def _enter_leg1(self, signal: SignalEvent) -> None:
        quote = self.latest_quotes.get(signal.side)
        if not quote:
            return
        if not self.risk.can_trade():
            return
        size = self._calculate_size(quote.best_ask)
        if size <= 0:
            return
        order = OrderRequest(
            side=signal.side,
            price=self._apply_slippage(quote.best_ask),
            size=size,
            client_order_id=generate_client_order_id("leg1"),
        )
        self.risk.register_order()
        result = await self._execute_with_requote(order, quote)
        if result.status != "filled":
            self.risk.register_failure()
            log_event(logger, "LEG1_NOT_FILLED", **asdict(result))
            return
        self.risk.register_success()
        self.risk.register_cycle_start()
        self.position = PositionState(
            leg1_side=signal.side,
            leg1_price=result.avg_price or order.price,
            leg1_size=result.filled_size,
            opened_at=datetime.now(timezone.utc),
        )
        self.journal.record(
            {
                "event": "leg1_filled",
                "side": signal.side,
                "price": self.position.leg1_price,
                "size": self.position.leg1_size,
            }
        )

    async def _evaluate_leg2(self, now: datetime) -> None:
        if not self.position:
            return
        elapsed = now - self.position.opened_at
        opposite = "DOWN" if self.position.leg1_side == "UP" else "UP"
        opposite_quote = self.latest_quotes.get(opposite)
        if not opposite_quote:
            return
        sum_price = self.position.leg1_price + opposite_quote.best_ask
        unrealized = (1.0 - sum_price) * self.position.leg1_size
        log_event(logger, "UNREALIZED_PNL", sum_price=sum_price, pnl=unrealized)
        if self._profit_lock_hit():
            await self._enter_leg2(opposite_quote, reason="profit_lock")
            return
        if sum_price <= self.config.strategy.sum_target:
            await self._enter_leg2(opposite_quote, reason="sum_target")
            return
        if elapsed.total_seconds() >= self.config.strategy.leg2_timeout_seconds:
            await self._handle_leg2_timeout(opposite_quote)

    def _profit_lock_hit(self) -> bool:
        if not self.position or self.config.strategy.profit_lock_bps <= 0:
            return False
        leg1_quote = self.latest_quotes.get(self.position.leg1_side)
        if not leg1_quote:
            return False
        move = (leg1_quote.best_bid - self.position.leg1_price) / self.position.leg1_price
        return move >= self.config.strategy.profit_lock_bps / 10000.0

    async def _handle_leg2_timeout(self, opposite_quote: Quote) -> None:
        if self.config.strategy.leg2_timeout_action == "skip":
            log_event(logger, "LEG2_TIMEOUT_SKIP")
            await self._close_cycle("timeout_skip")
            return
        sum_price = self.position.leg1_price + opposite_quote.best_ask
        if sum_price <= self.config.strategy.sum_target_max:
            await self._enter_leg2(opposite_quote, reason="timeout_defensive")
        else:
            log_event(logger, "LEG2_TIMEOUT_WAIT", sum_price=sum_price)

    async def _enter_leg2(self, quote: Quote, reason: str) -> None:
        if not self.position:
            return
        size = min(self.position.leg1_size, self._calculate_size(quote.best_ask))
        if size <= 0:
            return
        order = OrderRequest(
            side=quote.side,
            price=self._apply_slippage(quote.best_ask),
            size=size,
            client_order_id=generate_client_order_id("leg2"),
        )
        self.risk.register_order()
        result = await self._execute_with_requote(order, quote)
        if result.status != "filled":
            self.risk.register_failure()
            log_event(logger, "LEG2_NOT_FILLED", **asdict(result))
            return
        self.risk.register_success()
        self.position.leg2_side = quote.side
        self.position.leg2_price = result.avg_price or order.price
        self.position.leg2_size = result.filled_size
        self.journal.record(
            {
                "event": "leg2_filled",
                "side": quote.side,
                "price": self.position.leg2_price,
                "size": self.position.leg2_size,
                "reason": reason,
            }
        )
        await self._close_cycle("completed")

    async def _close_cycle(self, reason: str) -> None:
        if not self.position:
            return
        pnl = self._estimate_pnl()
        self.risk.record_pnl(pnl)
        self.journal.record(
            {
                "event": "cycle_closed",
                "reason": reason,
                "pnl_estimate": pnl,
                "leg1_side": self.position.leg1_side,
                "leg1_price": self.position.leg1_price,
                "leg2_side": self.position.leg2_side,
                "leg2_price": self.position.leg2_price,
            }
        )
        self.position = None
        self.risk.register_cycle_end()

    def _estimate_pnl(self) -> float:
        if not self.position or not self.position.leg2_price:
            return 0.0
        total_cost = self.position.leg1_price + self.position.leg2_price
        return (1.0 - total_cost) * self.position.leg1_size

    def _apply_slippage(self, price: float) -> float:
        return price * (1 + self.config.execution.slippage_bps / 10000.0)

    def _calculate_size(self, price: float) -> float:
        max_usd = min(self.config.risk.max_usd_per_leg, self.config.risk.bankroll_usd)
        if price <= 0:
            return 0.0
        return round(max_usd / price, 6)

    async def _execute_with_requote(self, order: OrderRequest, quote: Quote):
        result = await self.execution.execute_limit_gtc(order)
        if result.status == "filled":
            return result
        for _ in range(self.config.execution.max_requotes):
            refreshed = OrderRequest(
                side=order.side,
                price=self._apply_slippage(quote.best_ask),
                size=order.size,
                client_order_id=generate_client_order_id("req"),
            )
            result = await self.execution.execute_limit_gtc(refreshed)
            if result.status == "filled":
                return result
        return result
