import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Holding:
    symbol: str
    name: str
    type: str                      # "CEDEAR" | "LOCAL_STOCK"
    yfinance_ticker: str
    cedear_ratio: Optional[int]
    quantity: int
    avg_price_ars: float

    @property
    def cost_basis_ars(self) -> float:
        return self.quantity * self.avg_price_ars

    @property
    def is_cedear(self) -> bool:
        return self.type == "CEDEAR"


@dataclass
class Portfolio:
    holdings: list

    @property
    def total_cost_basis_ars(self) -> float:
        return sum(h.cost_basis_ars for h in self.holdings)


def load_portfolio(path: Path) -> Portfolio:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    holdings = []
    for item in data["holdings"]:
        required = ["symbol", "name", "type", "yfinance_ticker", "quantity", "avg_price_ars"]
        missing = [k for k in required if k not in item]
        if missing:
            raise ValueError(f"Holding '{item.get('symbol', '?')}' missing fields: {missing}")
        holdings.append(Holding(
            symbol=item["symbol"],
            name=item["name"],
            type=item["type"],
            yfinance_ticker=item["yfinance_ticker"],
            cedear_ratio=item.get("cedear_ratio"),
            quantity=item["quantity"],
            avg_price_ars=item["avg_price_ars"],
        ))
    return Portfolio(holdings=holdings)
