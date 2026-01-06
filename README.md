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
- `--order-size`: størrelsen på hver ordre (default 10)
- `--request-timeout`: HTTP-timeout i sekunder
- `--max-retries`: hvor mange ganger klienten prøver ved feil

Nøkler kan settes som env-variabler:

```
POLLYMARKET_API_KEY=din-nøkkel
POLLYMARKET_API_BASE=https://clob.polymarket.com
POLLYMARKET_POLL_INTERVAL=60
POLLYMARKET_MIN_EDGE_BPS=75
POLLYMARKET_MAX_ORDERS_PER_CYCLE=2
POLLYMARKET_ORDER_SIZE=15
POLLYMARKET_REQUEST_TIMEOUT=20
POLLYMARKET_MAX_RETRIES=5
```

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
