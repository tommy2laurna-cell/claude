from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from src.portfolio import Portfolio, Holding
from src.market_data import TickerData
from src.fx_rate import FXRate

ART = ZoneInfo("America/Argentina/Buenos_Aires")


@dataclass
class HoldingResult:
    symbol: str
    name: str
    ticker: str
    quantity: int
    # Prices
    prev_price_ars: float
    current_price_ars: float
    # Daily
    daily_change_pct: float
    daily_change_ars: float
    # Values
    prev_value_ars: float
    current_value_ars: float
    # Unrealised P&L vs cost basis
    cost_basis_ars: float
    unrealised_ars: float
    unrealised_pct: float
    # Portfolio weight
    weight_pct: float = 0.0
    # Whether price data was available
    data_available: bool = True


@dataclass
class PortfolioResult:
    holdings: list
    total_current_ars: float
    total_prev_ars: float
    total_daily_change_ars: float
    total_daily_change_pct: float
    total_cost_basis_ars: float
    total_unrealised_ars: float
    total_unrealised_pct: float
    ccl_rate: float
    ccl_source: str
    timestamp: str


def _estimate_ars_price(
    price_usd: float,
    ccl_rate: float,
    cedear_ratio: Optional[int],
) -> float:
    ratio = cedear_ratio if cedear_ratio and cedear_ratio > 0 else 1
    return price_usd * ccl_rate / ratio


def analyse_portfolio(
    portfolio: Portfolio,
    ticker_data: dict[str, TickerData],
    fx: FXRate,
) -> PortfolioResult:
    results: list[HoldingResult] = []

    for h in portfolio.holdings:
        td = ticker_data.get(h.yfinance_ticker)
        price = td.price if td else None

        if price and price.available:
            if h.type == "LOCAL_STOCK":
                prev_price_ars = price.prev_close
                current_price_ars = price.current_close
            else:
                prev_price_ars = _estimate_ars_price(price.prev_close, fx.usd_ars, h.cedear_ratio)
                current_price_ars = _estimate_ars_price(price.current_close, fx.usd_ars, h.cedear_ratio)

            prev_value = h.quantity * prev_price_ars
            current_value = h.quantity * current_price_ars
            daily_change_ars = current_value - prev_value
            daily_change_pct = price.change_pct
            data_ok = True
        else:
            prev_price_ars = h.avg_price_ars
            current_price_ars = h.avg_price_ars
            prev_value = h.cost_basis_ars
            current_value = h.cost_basis_ars
            daily_change_ars = 0.0
            daily_change_pct = 0.0
            data_ok = False

        cost = h.cost_basis_ars
        unrealised = current_value - cost
        unrealised_pct = (unrealised / cost * 100) if cost > 0 else 0.0

        results.append(HoldingResult(
            symbol=h.symbol,
            name=h.name,
            ticker=h.yfinance_ticker,
            quantity=h.quantity,
            prev_price_ars=prev_price_ars,
            current_price_ars=current_price_ars,
            daily_change_pct=daily_change_pct,
            daily_change_ars=daily_change_ars,
            prev_value_ars=prev_value,
            current_value_ars=current_value,
            cost_basis_ars=cost,
            unrealised_ars=unrealised,
            unrealised_pct=unrealised_pct,
            data_available=data_ok,
        ))

    total_current = sum(r.current_value_ars for r in results)
    total_prev = sum(r.prev_value_ars for r in results)
    total_cost = sum(r.cost_basis_ars for r in results)
    total_daily = total_current - total_prev
    total_daily_pct = (total_daily / total_prev * 100) if total_prev > 0 else 0.0
    total_unrealised = total_current - total_cost
    total_unrealised_pct = (total_unrealised / total_cost * 100) if total_cost > 0 else 0.0

    for r in results:
        r.weight_pct = (r.current_value_ars / total_current * 100) if total_current > 0 else 0.0

    return PortfolioResult(
        holdings=results,
        total_current_ars=total_current,
        total_prev_ars=total_prev,
        total_daily_change_ars=total_daily,
        total_daily_change_pct=total_daily_pct,
        total_cost_basis_ars=total_cost,
        total_unrealised_ars=total_unrealised,
        total_unrealised_pct=total_unrealised_pct,
        ccl_rate=fx.usd_ars,
        ccl_source=fx.source,
        timestamp=datetime.now(ART).strftime("%d/%m/%Y %H:%M ART"),
    )
