from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns

from src.analyzer import PortfolioResult, HoldingResult
from src.market_data import TickerData

console = Console()


def _ars(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}${v:,.0f}"


def _pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def _color(v: float) -> str:
    return "green" if v >= 0 else "red"


def render_terminal(result: PortfolioResult, ai_advice: str, ticker_data: dict[str, TickerData]) -> str:
    console.rule(f"[bold blue]Asesor de Portfolio — {result.timestamp}[/bold blue]")

    # Summary panel
    sign_color = _color(result.total_daily_change_ars)
    summary = (
        f"Valor total: [bold]${result.total_current_ars:,.0f} ARS[/bold]\n"
        f"Cambio del día: [{sign_color}]{_ars(result.total_daily_change_ars)} ({_pct(result.total_daily_change_pct)})[/{sign_color}]\n"
        f"P&L no realizado: [{_color(result.total_unrealised_ars)}]{_ars(result.total_unrealised_ars)} ({_pct(result.total_unrealised_pct)})[/{_color(result.total_unrealised_ars)}]\n"
        f"CCL: ${result.ccl_rate:,.2f} ARS/USD ({result.ccl_source})"
    )
    console.print(Panel(summary, title="Resumen", border_style="blue"))

    # Holdings table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Símbolo", style="bold")
    table.add_column("Empresa", max_width=22)
    table.add_column("Peso", justify="right")
    table.add_column("% Día", justify="right")
    table.add_column("Cambio ARS", justify="right")
    table.add_column("Valor ARS", justify="right")
    table.add_column("P&L No Real.", justify="right")

    for h in sorted(result.holdings, key=lambda x: x.weight_pct, reverse=True):
        color = _color(h.daily_change_pct)
        unr_color = _color(h.unrealised_pct)
        na = " ⚠" if not h.data_available else ""
        table.add_row(
            h.symbol,
            h.name,
            f"{h.weight_pct:.1f}%",
            Text(f"{_pct(h.daily_change_pct)}{na}", style=color),
            Text(_ars(h.daily_change_ars), style=color),
            f"${h.current_value_ars:,.0f}",
            Text(f"{_ars(h.unrealised_ars)} ({_pct(h.unrealised_pct)})", style=unr_color),
        )

    console.print(table)

    # News
    console.rule("[bold]Noticias (Últimas 36hs)[/bold]")
    any_news = False
    for h in result.holdings:
        td = ticker_data.get(h.ticker)
        if td and td.news:
            any_news = True
            console.print(f"\n[bold yellow]{h.symbol}[/bold yellow] — {h.name}")
            for n in td.news:
                console.print(f"  • [link={n.url}]{n.title}[/link]")
                console.print(f"    [dim]{n.publisher} — {n.published_utc}[/dim]")
    if not any_news:
        console.print("[dim]Sin noticias relevantes en las últimas 36 horas.[/dim]")

    # AI advice
    console.print()
    console.print(Panel(ai_advice, title="[bold magenta]Análisis IA[/bold magenta]", border_style="magenta"))
    console.rule()

    # Return plain-text version for email
    return _build_plain_text(result, ai_advice, ticker_data)


def _build_plain_text(result: PortfolioResult, ai_advice: str, ticker_data: dict[str, TickerData]) -> str:
    lines = [
        f"ASESOR DE PORTFOLIO — {result.timestamp}",
        "=" * 55,
        "",
        "RESUMEN",
        f"  Valor total:       ${result.total_current_ars:,.0f} ARS",
        f"  Cambio del día:    {_ars(result.total_daily_change_ars)} ({_pct(result.total_daily_change_pct)})",
        f"  P&L no realizado:  {_ars(result.total_unrealised_ars)} ({_pct(result.total_unrealised_pct)})",
        f"  CCL:               ${result.ccl_rate:,.2f} ARS/USD ({result.ccl_source})",
        "",
        "POSICIONES",
        f"{'Símbolo':<8} {'Peso':>6} {'% Día':>8} {'Cambio ARS':>13} {'Valor ARS':>14} {'P&L NR':>14}",
        "-" * 70,
    ]
    for h in sorted(result.holdings, key=lambda x: x.weight_pct, reverse=True):
        na = "*" if not h.data_available else ""
        lines.append(
            f"{h.symbol:<8} {h.weight_pct:>5.1f}% {_pct(h.daily_change_pct)+na:>8} "
            f"{_ars(h.daily_change_ars):>13} ${h.current_value_ars:>13,.0f} "
            f"{_ars(h.unrealised_ars):>14}"
        )

    lines += ["", "NOTICIAS (ÚLTIMAS 36hs)", "-" * 40]
    any_news = False
    for h in result.holdings:
        td = ticker_data.get(h.ticker)
        if td and td.news:
            any_news = True
            lines.append(f"\n{h.symbol} — {h.name}")
            for n in td.news:
                lines.append(f"  • {n.title}")
                lines.append(f"    {n.publisher} — {n.published_utc}")
                lines.append(f"    {n.url}")
    if not any_news:
        lines.append("Sin noticias relevantes.")

    lines += ["", "ANÁLISIS IA", "-" * 40, ai_advice, ""]
    return "\n".join(lines)


def build_html_email(result: PortfolioResult, ai_advice: str, ticker_data: dict[str, TickerData]) -> str:
    green = "#16a34a"
    red = "#dc2626"
    blue = "#4f46e5"

    def val_color(v: float) -> str:
        return green if v >= 0 else red

    rows = ""
    for h in sorted(result.holdings, key=lambda x: x.weight_pct, reverse=True):
        c = val_color(h.daily_change_pct)
        uc = val_color(h.unrealised_pct)
        na = " ⚠" if not h.data_available else ""
        rows += (
            f"<tr>"
            f"<td style='font-weight:bold'>{h.symbol}</td>"
            f"<td>{h.name}</td>"
            f"<td style='text-align:right'>{h.weight_pct:.1f}%</td>"
            f"<td style='text-align:right;color:{c}'>{_pct(h.daily_change_pct)}{na}</td>"
            f"<td style='text-align:right;color:{c}'>{_ars(h.daily_change_ars)}</td>"
            f"<td style='text-align:right'>${h.current_value_ars:,.0f}</td>"
            f"<td style='text-align:right;color:{uc}'>{_ars(h.unrealised_ars)} ({_pct(h.unrealised_pct)})</td>"
            f"</tr>"
        )

    news_html = ""
    any_news = False
    for h in result.holdings:
        td = ticker_data.get(h.ticker)
        if td and td.news:
            any_news = True
            news_html += f"<p><strong>{h.symbol} — {h.name}</strong></p><ul>"
            for n in td.news:
                news_html += f"<li><a href='{n.url}'>{n.title}</a> — {n.publisher}, {n.published_utc}</li>"
            news_html += "</ul>"
    if not any_news:
        news_html = "<p><em>Sin noticias relevantes en las últimas 36 horas.</em></p>"

    day_color = val_color(result.total_daily_change_ars)
    unr_color = val_color(result.total_unrealised_ars)
    ai_html = ai_advice.replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body style='font-family:Arial,sans-serif;max-width:780px;margin:auto;padding:20px;color:#1e1e2e'>
  <h1 style='color:{blue};border-bottom:2px solid {blue};padding-bottom:8px'>
    Asesor de Portfolio — {result.timestamp}
  </h1>

  <table style='width:100%;border-collapse:collapse;margin-bottom:24px;background:#f8f8ff;border-radius:8px'>
    <tr>
      <td style='padding:12px'><strong>Valor total</strong><br><span style='font-size:1.4em'>${result.total_current_ars:,.0f} ARS</span></td>
      <td style='padding:12px'><strong>Cambio del día</strong><br><span style='font-size:1.2em;color:{day_color}'>{_ars(result.total_daily_change_ars)} ({_pct(result.total_daily_change_pct)})</span></td>
      <td style='padding:12px'><strong>P&L No Realizado</strong><br><span style='color:{unr_color}'>{_ars(result.total_unrealised_ars)} ({_pct(result.total_unrealised_pct)})</span></td>
      <td style='padding:12px'><strong>CCL</strong><br>${result.ccl_rate:,.2f} ARS/USD<br><small style='color:#666'>{result.ccl_source}</small></td>
    </tr>
  </table>

  <h2>Posiciones</h2>
  <table style='width:100%;border-collapse:collapse;font-size:0.9em'>
    <thead>
      <tr style='background:{blue};color:white'>
        <th style='padding:8px;text-align:left'>Símbolo</th>
        <th style='padding:8px;text-align:left'>Empresa</th>
        <th style='padding:8px;text-align:right'>Peso</th>
        <th style='padding:8px;text-align:right'>% Día</th>
        <th style='padding:8px;text-align:right'>Cambio ARS</th>
        <th style='padding:8px;text-align:right'>Valor ARS</th>
        <th style='padding:8px;text-align:right'>P&L No Real.</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Noticias (Últimas 36hs)</h2>
  {news_html}

  <h2 style='color:#7c3aed'>Análisis IA</h2>
  <div style='background:#faf5ff;border-left:4px solid #7c3aed;padding:16px;border-radius:4px'>
    {ai_html}
  </div>

  <p style='color:#999;font-size:0.75em;margin-top:32px;border-top:1px solid #eee;padding-top:8px'>
    Este reporte es generado automáticamente con fines informativos únicamente.
    No constituye asesoramiento financiero profesional. Invertir implica riesgos.
  </p>
</body>
</html>"""
