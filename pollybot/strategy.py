from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MarketSignal:
    market_id: str
    outcome: str
    size: float
    price: float
    reason: str


def find_edges(
    markets: list[dict[str, Any]], *, min_edge_bps: float, max_orders: int, order_size: float
) -> list[MarketSignal]:
    """Pick simple opportunities based on outcome probability mispricing.

    The heuristic looks for markets with both "yes" and "no" prices where the
    spread implies a combined probability below 1.0 by the provided basis points.
    """

    signals: list[MarketSignal] = []
    for market in markets:
        if len(signals) >= max_orders:
            break
        outcomes = market.get("outcomes") or []
        if len(outcomes) < 2:
            continue
        yes_price = next((o.get("price") for o in outcomes if o.get("name", "").lower() == "yes"), None)
        no_price = next((o.get("price") for o in outcomes if o.get("name", "").lower() == "no"), None)
        if yes_price is None or no_price is None:
            continue
        edge = (1 - (yes_price + no_price)) * 10_000  # basis points
        if edge >= min_edge_bps:
            signals.append(
                MarketSignal(
                    market_id=str(market.get("id")),
                    outcome="yes" if yes_price < no_price else "no",
                    size=order_size,
                    price=yes_price if yes_price < no_price else no_price,
                    reason=f"Edge {edge:.0f} bps on {market.get('question', 'unknown')}",
                )
            )
    return signals
