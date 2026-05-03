import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Holding:
    symbol: str
    name: str
    type: str               # "CEDEAR" | "LOCAL_STOCK"
    yfinance_ticker: str
    value_ars: float        # valor actual de la posición en ARS (de la app)
    return_pct: float       # rendimiento acumulado en % (de la app)

    @property
    def cost_basis_ars(self) -> float:
        # Invertimos el rendimiento para obtener el costo original
        return self.value_ars / (1 + self.return_pct / 100)

    @property
    def unrealised_ars(self) -> float:
        return self.value_ars - self.cost_basis_ars


@dataclass
class Portfolio:
    holdings: list

    @property
    def total_value_ars(self) -> float:
        return sum(h.value_ars for h in self.holdings)

    @property
    def total_cost_basis_ars(self) -> float:
        return sum(h.cost_basis_ars for h in self.holdings)


def load_portfolio(path: Path) -> Portfolio:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    holdings = []
    for item in data["holdings"]:
        required = ["symbol", "name", "type", "yfinance_ticker", "value_ars", "return_pct"]
        missing = [k for k in required if k not in item]
        if missing:
            raise ValueError(f"Holding '{item.get('symbol', '?')}' falta: {missing}")
        holdings.append(Holding(
            symbol=item["symbol"],
            name=item["name"],
            type=item["type"],
            yfinance_ticker=item["yfinance_ticker"],
            value_ars=item["value_ars"],
            return_pct=item["return_pct"],
        ))
    return Portfolio(holdings=holdings)
