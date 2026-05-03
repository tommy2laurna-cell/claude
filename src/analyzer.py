from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.portfolio import Portfolio
from src.market_data import TickerData
from src.fx_rate import FXRate

ART = ZoneInfo("America/Argentina/Buenos_Aires")


@dataclass
class HoldingResult:
    symbol: str
    name: str
    ticker: str
    # Valores en ARS
    ref_value_ars: float        # valor de referencia (portfolio.json)
    current_value_ars: float    # estimado con cambio del día aplicado
    daily_change_pct: float
    daily_change_ars: float
    # P&L acumulado
    cost_basis_ars: float
    unrealised_ars: float
    unrealised_pct: float
    # Peso en el portfolio
    weight_pct: float = 0.0
    data_available: bool = True


@dataclass
class PortfolioResult:
    holdings: list
    total_current_ars: float
    total_ref_ars: float
    total_daily_change_ars: float
    total_daily_change_pct: float
    total_cost_basis_ars: float
    total_unrealised_ars: float
    total_unrealised_pct: float
    ccl_rate: float
    ccl_source: str
    timestamp: str


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
            # Aplicamos el % de cambio del día sobre el valor de referencia en ARS
            daily_pct = price.change_pct
            daily_ars = h.value_ars * (daily_pct / 100)
            current_value = h.value_ars + daily_ars
            data_ok = True
        else:
            daily_pct = 0.0
            daily_ars = 0.0
            current_value = h.value_ars
            data_ok = False

        cost = h.cost_basis_ars
        unrealised = current_value - cost
        unrealised_pct = (unrealised / cost * 100) if cost != 0 else 0.0

        results.append(HoldingResult(
            symbol=h.symbol,
            name=h.name,
            ticker=h.yfinance_ticker,
            ref_value_ars=h.value_ars,
            current_value_ars=current_value,
            daily_change_pct=daily_pct,
            daily_change_ars=daily_ars,
            cost_basis_ars=cost,
            unrealised_ars=unrealised,
            unrealised_pct=unrealised_pct,
            data_available=data_ok,
        ))

    total_ref = sum(r.ref_value_ars for r in results)
    total_current = sum(r.current_value_ars for r in results)
    total_cost = sum(r.cost_basis_ars for r in results)
    total_daily = total_current - total_ref
    total_daily_pct = (total_daily / total_ref * 100) if total_ref > 0 else 0.0
    total_unrealised = total_current - total_cost
    total_unrealised_pct = (total_unrealised / total_cost * 100) if total_cost > 0 else 0.0

    for r in results:
        r.weight_pct = (r.current_value_ars / total_current * 100) if total_current > 0 else 0.0

    return PortfolioResult(
        holdings=results,
        total_current_ars=total_current,
        total_ref_ars=total_ref,
        total_daily_change_ars=total_daily,
        total_daily_change_pct=total_daily_pct,
        total_cost_basis_ars=total_cost,
        total_unrealised_ars=total_unrealised,
        total_unrealised_pct=total_unrealised_pct,
        ccl_rate=fx.usd_ars,
        ccl_source=fx.source,
        timestamp=datetime.now(ART).strftime("%d/%m/%Y %H:%M ART"),
    )
