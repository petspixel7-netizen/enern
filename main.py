from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from pollybot.config import BotConfig
from pollybot.service import run_bot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="24/7 Pollymarket trading bot")
    parser.add_argument("--dry-run", action="store_true", help="Log signals without submitting orders")
    parser.add_argument("--poll-interval", type=float, help="Seconds between polling cycles")
    parser.add_argument("--min-edge-bps", type=float, help="Minimum edge (basis points) to trade")
    parser.add_argument("--max-orders", type=int, help="Maximum number of orders per cycle")
    parser.add_argument("--request-timeout", type=float, help="HTTP timeout in seconds")
    parser.add_argument("--max-retries", type=int, help="Number of retries on transient failures")
    parser.add_argument("--bankroll", type=float, help="Total bankroll for risk sizing")
    parser.add_argument("--risk-per-trade-pct", type=float, help="Risk per trade as fraction (e.g. 0.005)")
    parser.add_argument("--max-trades-per-day", type=int, help="Maximum trades allowed per UTC day")
    parser.add_argument("--daily-loss-limit-pct", type=float, help="Stop trading when losses hit this fraction")
    parser.add_argument("--max-consecutive-losses", type=int, help="Pause when this many losses occur")
    parser.add_argument("--cooldown-hours", type=int, help="Hours to pause after max consecutive losses")
    parser.add_argument("--hourly-scan", action="store_true", help="Run edge detection once per hour")
    parser.add_argument("--market-cooldown-hours", type=int, help="Minimum hours between trades per market")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> BotConfig:
    config = BotConfig()
    if args.poll_interval:
        config.poll_interval = args.poll_interval
    if args.min_edge_bps:
        config.min_edge_bps = args.min_edge_bps
    if args.max_orders:
        config.max_orders_per_cycle = args.max_orders
    if args.request_timeout:
        config.request_timeout = args.request_timeout
    if args.max_retries:
        config.max_retries = args.max_retries
    if args.bankroll:
        config.bankroll = args.bankroll
    if args.risk_per_trade_pct:
        config.risk_per_trade_pct = args.risk_per_trade_pct
    if args.max_trades_per_day:
        config.max_trades_per_day = args.max_trades_per_day
    if args.daily_loss_limit_pct:
        config.daily_loss_limit_pct = args.daily_loss_limit_pct
    if args.max_consecutive_losses:
        config.max_consecutive_losses = args.max_consecutive_losses
    if args.cooldown_hours:
        config.cooldown_hours = args.cooldown_hours
    if args.hourly_scan:
        config.hourly_scan = True
    if args.market_cooldown_hours:
        config.market_cooldown_hours = args.market_cooldown_hours
    config.dry_run = args.dry_run
    return config


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    args = parse_args()
    config = build_config(args)
    try:
        asyncio.run(run_bot(config))
    except KeyboardInterrupt:
        logging.info("Bot interrupted, shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
