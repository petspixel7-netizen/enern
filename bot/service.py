from __future__ import annotations

import asyncio
import logging
from typing import Optional

from bot.config import BotConfig
from bot.datafeed import MovementDetector, PolymarketDatafeed
from bot.execution import ExecutionEngine, PolymarketExecutionAdapter
from bot.logger import Journal, log_event
from bot.risk import RiskManager
from bot.strategy import DipHedgeStrategy

logger = logging.getLogger(__name__)


class BotService:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.datafeed = PolymarketDatafeed(config)
        self.execution_adapter = PolymarketExecutionAdapter(config)
        self.execution_engine = ExecutionEngine(config, self.execution_adapter)
        self.risk = RiskManager(config)
        self.journal = Journal(config.journal_dir)
        self.strategy = DipHedgeStrategy(config, self.execution_engine, self.risk, self.journal)
        self.detector = MovementDetector(config)
        self._running = True

    async def run(self) -> None:
        log_event(logger, "BOT_START", market=self.config.market, dry_run=self.config.dry_run)
        try:
            async for quote in self.datafeed.stream():
                await self.strategy.on_quote(quote)
                signal = self.detector.update(quote)
                if signal:
                    await self.strategy.on_signal(signal)
                if not self._running:
                    break
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fatal bot error: %s", exc)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        await self.datafeed.close()
        await self.execution_adapter.close()
        log_event(logger, "BOT_STOP")

    def stop(self) -> None:
        self._running = False


async def run_bot(config: BotConfig) -> None:
    service = BotService(config)
    await service.run()
