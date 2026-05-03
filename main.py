"""
Asesor Financiero de Portfolio CEDEAR (Argentina)

Script de una sola ejecución — el scheduling lo maneja el sistema (cron).

Uso:
  python main.py          — ejecuta si hoy es día hábil, sino sale sin hacer nada
  python main.py --force  — ejecuta sin importar el día (útil para pruebas)

Cron recomendado (corre todos los días hábiles a las 17:30 ART):
  30 17 * * 1-5  cd /ruta/al/proyecto && python main.py
"""
import sys
from rich.console import Console

from src.config import Config
from src.portfolio import load_portfolio
from src.market_data import fetch_all_tickers
from src.fx_rate import fetch_ccl_rate
from src.analyzer import analyse_portfolio
from src.ai_advisor import get_ai_advice
from src.report import render_terminal
from src.holidays import should_run_today
from src.output.email_adapter import EmailAdapter

console = Console()


def main() -> None:
    force = "--force" in sys.argv

    if not force and not should_run_today():
        console.print("[yellow]Hoy no es día hábil en Argentina. Nada que hacer.[/yellow]")
        return

    config = Config()

    portfolio = load_portfolio(config.portfolio_path)
    if not portfolio.holdings:
        console.print("[red]portfolio.json está vacío. Completá tus posiciones primero.[/red]")
        sys.exit(1)

    tickers = [h.yfinance_ticker for h in portfolio.holdings]

    console.print(f"Obteniendo precios: {', '.join(tickers)}...")
    ticker_data = fetch_all_tickers(tickers, news_max_items=config.news_max_items)

    console.print("Obteniendo tipo de cambio CCL...")
    fx = fetch_ccl_rate()

    result = analyse_portfolio(portfolio, ticker_data, fx)

    console.print("Consultando Claude para el análisis...")
    ai_advice = get_ai_advice(result, ticker_data, config)

    plain_text = render_terminal(result, ai_advice, ticker_data)

    if config.email_configured:
        console.print("Enviando email...")
        EmailAdapter(config).send(result, plain_text, ai_advice, ticker_data)
        console.print(f"[green]Email enviado a {config.email_to}[/green]")
    else:
        console.print("[yellow]Email no configurado — completá EMAIL_* en .env[/yellow]")


if __name__ == "__main__":
    main()
