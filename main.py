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
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> BotConfig:
    config = BotConfig()
    if args.poll_interval:
        config.poll_interval = args.poll_interval
    if args.min_edge_bps:
        config.min_edge_bps = args.min_edge_bps
    if args.max_orders:
        config.max_orders_per_cycle = args.max_orders
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
