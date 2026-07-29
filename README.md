# Polymarket Event-Driven Dip/Hedge Bot (Python 3.11)

A Windows-friendly, event-driven Polymarket CLOB bot that only trades when a configurable
movement trigger occurs. It executes a 2-leg dip/hedge strategy on short-duration crypto
markets (e.g., BTC 15m UP/DOWN). The bot is idle otherwise.

## Strategy Summary

1. **Leg1 (Dip/Pump Trigger)**
   - Detects a fast price movement inside a rolling window (default 3 seconds).
   - When a dump or pump threshold is crossed (default 10%), it buys the moved side.

2. **Leg2 (Hedge)**
   - Buys the opposite side only when:
     - `leg1EntryPrice + oppositeBestAsk <= sumTarget` **OR**
     - `profitLockBps` condition is met.
   - If Leg2 times out (default 180s), it either:
     - Places a defensive hedge at `sumTargetMax`, or
     - Skips and waits for the next cycle (configurable).

## Quickstart (Windows)

```powershell
# From repository root
.\scripts\run_windows.ps1
```

## Dry-run first

Dry-run is enabled by default in `config.yaml` and can be forced with CLI:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --dry-run
```

## How to set .env

```powershell
Copy-Item -Path .env.example -Destination .env -Force
notepad .env
```

Add your Polymarket API credentials:

```
POLYMARKET_API_KEY="your_key"
POLYMARKET_API_SECRET="your_secret"
```

## How to select market

Update `config.yaml` or override on the CLI:

```powershell
python main.py --market BTC-15M
```

## Safety/risk notes

- **Bankroll:** $50 assumed, with strict risk caps per leg (default $1.50).
- **Max active positions:** 1 at a time.
- **Cooldown:** 120 seconds after a completed 2-leg cycle.
- **Daily loss limit:** $5.00 (trading stops for the day).
- **Circuit breaker:** after 3 consecutive failed fills or API errors, pause for 30 minutes.
- **Order policy:** LIMIT + GTC at best ask (or better) with slippage guard.

## Configuration

All parameters live in `config.yaml`. CLI flags override config values.

```powershell
python main.py --market BTC-15M --max-usd-per-leg 1.25 --move-pct-threshold 8
```

## Project layout

```
main.py
config.yaml
bot/
  config.py
  datafeed.py
  execution.py
  logger.py
  risk.py
  strategy.py
  service.py
  types.py
scripts/
  run_windows.ps1
logs/
  trades.jsonl
  trades.csv
```

## Datafeed notes

- WebSocket is preferred if available (`datafeed.mode: websocket`).
- If WebSocket is unavailable, switch to `polling` in `config.yaml`.
- The adapter layer in `bot/datafeed.py` shows where to plug official CLOB endpoints.

## Execution notes

- The execution adapter uses REST endpoints and includes placeholders to plug
  Polymarket's official signing and order endpoints.
- Dry-run mode logs all actions without placing orders.
