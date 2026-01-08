from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Quote:
    side: str
    best_bid: float
    best_ask: float
    liquidity: float
    spread: float
    timestamp: datetime


@dataclass
class SignalEvent:
    timestamp: datetime
    side: str
    entry_price: float
    move_pct: float
    spread: float
    liquidity: float


@dataclass
class OrderRequest:
    side: str
    price: float
    size: float
    client_order_id: str


@dataclass
class OrderResult:
    order_id: str
    filled_size: float
    avg_price: float
    status: str
    remaining_size: float
    error: Optional[str] = None


@dataclass
class PositionState:
    leg1_side: str
    leg1_price: float
    leg1_size: float
    opened_at: datetime
    leg2_side: Optional[str] = None
    leg2_price: Optional[float] = None
    leg2_size: Optional[float] = None
