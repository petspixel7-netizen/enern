from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Optional

from bot.config import BotConfig

logger = logging.getLogger(__name__)


@dataclass
class RiskState:
    active_positions: int = 0
    daily_loss_usd: float = 0.0
    last_cycle_end: Optional[datetime] = None
    orders_last_hour: Deque[datetime] = None
    consecutive_failures: int = 0
    circuit_breaker_until: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.orders_last_hour is None:
            self.orders_last_hour = deque()


class RiskManager:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.state = RiskState()

    def can_trade(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.state.circuit_breaker_until and now < self.state.circuit_breaker_until:
            logger.warning("Circuit breaker active until %s", self.state.circuit_breaker_until)
            return False
        if self.state.active_positions >= self.config.risk.max_active_positions:
            return False
        if self.state.daily_loss_usd >= self.config.risk.daily_loss_limit_usd:
            logger.warning("Daily loss limit reached")
            return False
        if self.state.last_cycle_end:
            delta = now - self.state.last_cycle_end
            if delta.total_seconds() < self.config.risk.cooldown_seconds:
                return False
        self._trim_hourly(now)
        if len(self.state.orders_last_hour) >= self.config.risk.max_orders_per_hour:
            logger.warning("Hourly order limit reached")
            return False
        return True

    def register_order(self) -> None:
        now = datetime.now(timezone.utc)
        self.state.orders_last_hour.append(now)
        self._trim_hourly(now)

    def register_cycle_start(self) -> None:
        self.state.active_positions += 1

    def register_cycle_end(self) -> None:
        self.state.active_positions = max(self.state.active_positions - 1, 0)
        self.state.last_cycle_end = datetime.now(timezone.utc)

    def register_failure(self) -> None:
        self.state.consecutive_failures += 1
        if self.state.consecutive_failures >= self.config.risk.circuit_breaker_failures:
            self.state.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(
                seconds=self.config.risk.circuit_breaker_cooldown_seconds
            )
            logger.error("Circuit breaker triggered")

    def register_success(self) -> None:
        self.state.consecutive_failures = 0

    def record_pnl(self, pnl_usd: float) -> None:
        self.state.daily_loss_usd += max(-pnl_usd, 0.0)

    def _trim_hourly(self, now: datetime) -> None:
        cutoff = now - timedelta(hours=1)
        while self.state.orders_last_hour and self.state.orders_last_hour[0] < cutoff:
            self.state.orders_last_hour.popleft()
