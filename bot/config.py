from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


@dataclass
class DatafeedConfig:
    mode: str = "websocket"
    ws_url: str = "wss://clob.polymarket.com/ws"
    rest_url: str = "https://clob.polymarket.com"
    orderbook_path: str = "/book"
    poll_interval_seconds: float = 1.0
    backoff_max_seconds: float = 15.0


@dataclass
class ExecutionConfig:
    rest_url: str = "https://clob.polymarket.com"
    order_path: str = "/orders"
    order_status_path: str = "/orders/{order_id}"
    cancel_path: str = "/orders/{order_id}"
    request_timeout_seconds: float = 10.0
    order_ttl_seconds: float = 15.0
    max_requotes: int = 1
    slippage_bps: float = 5.0


@dataclass
class StrategyConfig:
    trigger_mode: str = "dump"  # dump or pump
    move_window_seconds: int = 3
    move_pct_threshold: float = 10.0
    sum_target: float = 0.95
    sum_target_max: float = 0.99
    profit_lock_bps: float = 0.0
    leg2_timeout_seconds: int = 180
    leg2_timeout_action: str = "defensive_hedge"  # defensive_hedge or skip


@dataclass
class RiskConfig:
    bankroll_usd: float = 50.0
    max_usd_per_leg: float = 1.5
    max_active_positions: int = 1
    cooldown_seconds: int = 120
    max_orders_per_hour: int = 30
    daily_loss_limit_usd: float = 5.0
    circuit_breaker_failures: int = 3
    circuit_breaker_cooldown_seconds: int = 1800


@dataclass
class BotConfig:
    market: str = "BTC-15M"
    dry_run: bool = True
    log_level: str = "INFO"
    journal_dir: Path = field(default_factory=lambda: Path("logs"))
    datafeed: DatafeedConfig = field(default_factory=DatafeedConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)

    @classmethod
    def load(cls, path: Path) -> "BotConfig":
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        raw = _load_config_file(path)
        return _merge_config(cls(), raw)



def _load_config_file(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text()) or {}
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text())
    raise ValueError("Unsupported config format; use .yaml or .json")


def _merge_config(config: BotConfig, raw: Dict[str, Any]) -> BotConfig:
    datafeed = raw.get("datafeed", {})
    execution = raw.get("execution", {})
    strategy = raw.get("strategy", {})
    risk = raw.get("risk", {})

    for key, value in raw.items():
        if hasattr(config, key) and key not in {"datafeed", "execution", "strategy", "risk"}:
            setattr(config, key, value)

    for key, value in datafeed.items():
        if hasattr(config.datafeed, key):
            setattr(config.datafeed, key, value)

    for key, value in execution.items():
        if hasattr(config.execution, key):
            setattr(config.execution, key, value)

    for key, value in strategy.items():
        if hasattr(config.strategy, key):
            setattr(config.strategy, key, value)

    for key, value in risk.items():
        if hasattr(config.risk, key):
            setattr(config.risk, key, value)

    return config


def load_env() -> None:
    load_dotenv()


def apply_cli_overrides(config: BotConfig, args: argparse.Namespace) -> BotConfig:
    if args.dry_run is not None:
        config.dry_run = args.dry_run
    if args.market:
        config.market = args.market
    if args.max_usd_per_leg is not None:
        config.risk.max_usd_per_leg = args.max_usd_per_leg
    if args.move_pct_threshold is not None:
        config.strategy.move_pct_threshold = args.move_pct_threshold
    if args.sum_target is not None:
        config.strategy.sum_target = args.sum_target
    if args.log_level:
        config.log_level = args.log_level
    if args.datafeed_mode:
        config.datafeed.mode = args.datafeed_mode
    return config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Event-driven Polymarket CLOB bot")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--market", help="Market slug or ID")
    parser.add_argument("--max-usd-per-leg", type=float)
    parser.add_argument("--move-pct-threshold", type=float)
    parser.add_argument("--sum-target", type=float)
    parser.add_argument("--datafeed-mode", choices=["websocket", "polling"], help="Override datafeed mode")
    parser.add_argument("--log-level", help="Logging level (INFO, DEBUG)")
    return parser
