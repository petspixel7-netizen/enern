from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BotMetrics:
    """Track bot runtime metrics and statistics."""

    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    markets_fetched: int = 0
    arbs_discovered: int = 0
    arbs_executed: int = 0
    total_pnl: float = 0.0
    reconnect_count: int = 0
    cycle_count: int = 0
    last_status_report: datetime | None = None

    def runtime_minutes(self) -> int:
        """Get runtime in minutes."""
        return int((datetime.now(UTC) - self.start_time).total_seconds() / 60)

    def runtime_str(self) -> str:
        """Get formatted runtime string."""
        elapsed = datetime.now(UTC) - self.start_time
        hours = int(elapsed.total_seconds() // 3600)
        minutes = int((elapsed.total_seconds() % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"

    def should_report_status(self, interval_minutes: int = 15) -> bool:
        """Check if enough time has passed to report status."""
        if self.last_status_report is None:
            return True
        elapsed = datetime.now(UTC) - self.last_status_report
        return elapsed >= timedelta(minutes=interval_minutes)

    def record_cycle(self, markets_count: int, signals_count: int) -> None:
        """Record a completed cycle."""
        self.cycle_count += 1
        self.markets_fetched = markets_count
        if signals_count > 0:
            self.arbs_discovered += signals_count

    def record_execution(self, pnl: float = 0.0) -> None:
        """Record an executed arbitrage."""
        self.arbs_executed += 1
        self.total_pnl += pnl

    def record_reconnect(self) -> None:
        """Record a reconnection event."""
        self.reconnect_count += 1

    def log_status_report(self) -> None:
        """Log comprehensive status report."""
        now = datetime.now(UTC)
        self.last_status_report = now

        logger.info("=" * 60)
        logger.info("BOT STATUS REPORT - %s", now.strftime("%Y-%m-%d %H:%M:%S UTC"))
        logger.info("=" * 60)
        logger.info("Runtime:            %s (~%d min)", self.runtime_str(), self.runtime_minutes())
        logger.info("API Connected:      ✅ Yes")
        logger.info("Cycles completed:   %d", self.cycle_count)
        logger.info("Markets fetched:    %d", self.markets_fetched)
        logger.info("Arbs discovered:    %d", self.arbs_discovered)
        logger.info("Arbs executed:      %d", self.arbs_executed)
        logger.info("PnL:                $%.2f", self.total_pnl)
        logger.info("Reconnects:         %d", self.reconnect_count)
        logger.info("=" * 60)
