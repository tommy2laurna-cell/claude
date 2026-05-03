import anthropic
from src.analyzer import PortfolioResult, HoldingResult
from src.market_data import TickerData
from src.config import Config

SYSTEM_PROMPT = (
    "Sos un analista financiero especializado en mercados argentinos e inversiones en CEDEARs. "
    "Brindás análisis claros y accionables para inversores minoristas argentinos. "
    "Conocés el contexto único del mercado local: inflación, devaluación del peso, "
    "tipo de cambio CCL/dólar blue, horarios del BYMA y cómo se comportan los CEDEARs "
    "respecto a sus subyacentes en Estados Unidos. "
    "Siempre incluís un aviso de riesgo y aclarás que tu análisis es informativo, "
    "no constituye asesoramiento financiero profesional."
)


def _fmt_ars(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}${v:,.0f}"


def _fmt_pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def build_prompt(result: PortfolioResult, ticker_data: dict[str, TickerData]) -> str:
    lines = [
        f"## Análisis de Cartera CEDEAR — {result.timestamp}",
        "",
        "### Resumen del Portafolio",
        f"- Valor total actual: ${result.total_current_ars:,.0f} ARS",
        f"- Cambio diario estimado: {_fmt_ars(result.total_daily_change_ars)} ({_fmt_pct(result.total_daily_change_pct)})",
        f"- Costo original (base): ${result.total_cost_basis_ars:,.0f} ARS",
        f"- Ganancia/pérdida no realizada: {_fmt_ars(result.total_unrealised_ars)} ({_fmt_pct(result.total_unrealised_pct)})",
        f"- Tipo de cambio CCL usado: ${result.ccl_rate:,.2f} ARS/USD (fuente: {result.ccl_source})",
        "",
        "### Performance Individual (Hoy)",
        "| Símbolo | Empresa | Peso | % Día | Cambio ARS | P&L No Real. |",
        "|---------|---------|------|-------|------------|-------------|",
    ]

    for h in sorted(result.holdings, key=lambda x: x.weight_pct, reverse=True):
        status = "" if h.data_available else " (sin datos)"
        lines.append(
            f"| {h.symbol} | {h.name} | {h.weight_pct:.1f}% | "
            f"{_fmt_pct(h.daily_change_pct)}{status} | "
            f"{_fmt_ars(h.daily_change_ars)} | "
            f"{_fmt_ars(h.unrealised_ars)} ({_fmt_pct(h.unrealised_pct)}) |"
        )

    lines += ["", "### Titulares de Noticias (Últimas 36hs)"]

    any_news = False
    no_news = []
    for h in result.holdings:
        td = ticker_data.get(h.ticker)
        if td and td.news:
            any_news = True
            lines.append(f"\n**{h.symbol} — {h.name}:**")
            for n in td.news:
                lines.append(f"- \"{n.title}\" — {n.publisher}, {n.published_utc}")
        else:
            no_news.append(h.symbol)

    if not any_news:
        lines.append("Sin noticias relevantes en las últimas 36 horas.")
    elif no_news:
        lines.append(f"\nSin noticias hoy: {', '.join(no_news)}")

    # Context
    winners = [h for h in result.holdings if h.daily_change_pct > 0 and h.data_available]
    losers = [h for h in result.holdings if h.daily_change_pct < 0 and h.data_available]
    top_winner = max(winners, key=lambda x: x.daily_change_pct, default=None)
    top_loser = min(losers, key=lambda x: x.daily_change_pct, default=None)

    lines += [
        "",
        "### Contexto",
        "- Mercados de EE.UU. cierran a las ~17:00 ART; BYMA ya cerrado al momento de este análisis",
    ]
    if top_winner:
        lines.append(f"- Mayor ganador del día: {top_winner.symbol} ({_fmt_pct(top_winner.daily_change_pct)})")
    if top_loser:
        lines.append(f"- Mayor perdedor del día: {top_loser.symbol} ({_fmt_pct(top_loser.daily_change_pct)})")

    local_weight = sum(h.weight_pct for h in result.holdings if h.symbol in ("VIST", "YPFD"))
    lines.append(f"- Exposición a activos locales argentinos (VIST + YPFD): {local_weight:.1f}%")

    lines += [
        "",
        "### Tu tarea",
        "Proporcioná el análisis en español con las siguientes secciones:",
        "1. **Resumen del día**: Principales factores del rendimiento (2-3 oraciones).",
        "2. **Movimientos destacados**: Breve comentario sobre activos que se movieron más de 2% hoy.",
        "3. **Impacto de noticias**: ¿Algún titular podría afectar estas posiciones en el corto plazo?",
        "4. **Vista de rebalanceo**: ¿Hay algún activo sobre o subponderado? Considerá que YPFD y VIST "
        "ofrecen cobertura en pesos frente a los CEDEARs en USD.",
        "5. **Acción recomendada**: Mantener / Rebalancear / Considerar aumentar posición — con justificación breve.",
        "6. **Aviso de riesgo**: Descargo estándar (1-2 oraciones).",
        "",
        "Extensión máxima: ~450 palabras. Tono: profesional pero accesible para un inversor minorista.",
    ]

    return "\n".join(lines)


def get_ai_advice(result: PortfolioResult, ticker_data: dict[str, TickerData], config: Config) -> str:
    try:
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        prompt = build_prompt(result, ticker_data)
        msg = client.messages.create(
            model=config.claude_model,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except anthropic.RateLimitError:
        return "[Análisis IA no disponible — límite de tasa alcanzado.]"
    except anthropic.APIError as e:
        return f"[Análisis IA no disponible — error de API: {e}]"
    except Exception as e:
        return f"[Análisis IA no disponible — error inesperado: {e}]"
