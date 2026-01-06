# Pollymarket 24/7 bot

En lettvekts Python-bot som kan kjøre kontinuerlig mot Pollymarkets offentlige API.
Strategien er enkel: den sjekker markedene for mulige arbitrage/edge-basert
tilbakekjøp mellom "yes"- og "no"-priser og legger inn ordre om differansen
oppfyller en minimumskrav i basispunkter.

> **Merk:** Handler krever `POLLYMARKET_API_KEY`. Uten API-nøkkel kjører boten i
> "read-only"-modus, henter markeder og logger signaler. Bekreft alltid mot
> Pollymarkets dokumentasjon og test i `--dry-run` før reell handel.

## Køring

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# Ingen eksterne avhengigheter nødvendig
python main.py --dry-run
```

Flagg:
- `--dry-run`: logger signaler uten å sende ordre
- `--poll-interval`: sekunder mellom hver syklus (default 30)
- `--min-edge-bps`: minste edge i basispunkter som må til før en handel
- `--max-orders`: maks antall ordre per syklus
- `--request-timeout`: HTTP-timeout i sekunder
- `--max-retries`: hvor mange ganger klienten prøver ved feil
- `--bankroll`: total bankroll som risiko kalkuleres fra
- `--risk-per-trade-pct`: prosent av bankroll risikert per handel (0.005 = 0.5 %)
- `--max-trades-per-day`: maks handler per UTC-dag
- `--daily-loss-limit-pct`: stopp grunnet daglig tap
- `--max-consecutive-losses`: pause etter X tap på rad
- `--cooldown-hours`: hvor lenge pausen varer
- `--hourly-scan`: kjør edge-deteksjon én gang i timen
- `--market-cooldown-hours`: minstetid mellom handler per marked

Nøkler kan settes som env-variabler:

```
POLLYMARKET_API_KEY=din-nøkkel
POLLYMARKET_API_BASE=https://clob.polymarket.com
POLLYMARKET_POLL_INTERVAL=60
POLLYMARKET_MIN_EDGE_BPS=75
POLLYMARKET_MAX_ORDERS_PER_CYCLE=2
POLLYMARKET_REQUEST_TIMEOUT=20
POLLYMARKET_MAX_RETRIES=5
RISK_PER_TRADE_PCT=0.005
MAX_TRADES_PER_DAY=10
DAILY_LOSS_LIMIT_PCT=0.02
MAX_CONSECUTIVE_LOSSES=3
COOLDOWN_HOURS=24
HOURLY_SCAN=true
MARKET_COOLDOWN_HOURS=3
POLLYBOT_BANKROLL=1000
```

> Risiko-parametre er fastlåst og følger medium-profilen: 0,5 % risiko pr
> handel, maks 10 handler per dag, daglig tapstak på 2 %, pause etter 3
> tap på rad med 24 timers cooldown. Ordrestørrelse beregnes alltid som
> `bankroll * RISK_PER_TRADE_PCT` (ingen faste beløp).

## Kjøre 24/7

- **tmux/screen:** start boten i en session, koble til ved behov.
- **systemd:** lag en servicefil som peker til `python /path/main.py` og sett
  `Restart=always` for å håndtere restarts.
- **Docker:** pakk koden i en minimal container og bruk `restart: always` i
  Compose/Kubernetes.

## Struktur

- `pollybot/config.py`: leser innstillinger fra miljø/CLI.
- `pollybot/client.py`: enkel HTTP-klient for Pollymarkets API.
- `pollybot/strategy.py`: heuristikk som finner potensielle handler.
- `pollybot/service.py`: orkestrerer sykluser og ordreutsending.
- `main.py`: CLI/entrypoint.

## Videre arbeid
- Bygg ekte risikostyring (størrelse per handel, stop-loss, caps per event).
- Legg til persistens (f.eks. SQLite) for utførte handler og PnL.
- Integrer robuste API-klienter (websocket streaming, signer, osv.).
