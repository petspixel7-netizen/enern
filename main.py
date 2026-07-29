from __future__ import annotations

import asyncio

from pathlib import Path

from bot.config import BotConfig, apply_cli_overrides, build_arg_parser, load_env
from bot.logger import setup_logging
from bot.service import run_bot


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    load_env()
    config = BotConfig.load(Path(args.config)) if Path(args.config).exists() else BotConfig()
    config = apply_cli_overrides(config, args)
    setup_logging(config.log_level)
    try:
        asyncio.run(run_bot(config))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
