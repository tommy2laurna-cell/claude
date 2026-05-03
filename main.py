"""
Asesor Financiero de Portfolio CEDEAR (Argentina)

Uso:
  python main.py           — inicia el scheduler (corre todos los días hábiles a las 17:30 ART)
  python main.py --now     — ejecuta el análisis inmediatamente (para pruebas)
  python main.py --force   — igual que --now, pero ignora si hoy es día hábil
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


def run_analysis(config: Config, force: bool = False) -> None:
    if not force and not should_run_today():
        console.print("[yellow]Hoy no es día hábil en Argentina. Saltando análisis.[/yellow]")
        console.print("[dim]Usá --force para ejecutar igual.[/dim]")
        return

    console.print("[bold blue]Iniciando análisis de portfolio...[/bold blue]")

    portfolio = load_portfolio(config.portfolio_path)
    if not portfolio.holdings:
        console.print("[red]El portfolio está vacío. Completá portfolio.json con tus posiciones.[/red]")
        return

    tickers = [h.yfinance_ticker for h in portfolio.holdings]

    console.print(f"  Obteniendo precios para: {', '.join(t for t in tickers)}...")
    ticker_data = fetch_all_tickers(tickers, news_max_items=config.news_max_items)

    console.print("  Obteniendo tipo de cambio CCL...")
    fx = fetch_ccl_rate()
    console.print(f"  CCL: ${fx.usd_ars:,.2f} ARS/USD (fuente: {fx.source})")

    result = analyse_portfolio(portfolio, ticker_data, fx)

    console.print("  Consultando IA para análisis y recomendaciones...")
    ai_advice = get_ai_advice(result, ticker_data, config)

    plain_text = render_terminal(result, ai_advice, ticker_data)

    if config.email_configured:
        console.print("  Enviando email...")
        try:
            adapter = EmailAdapter(config)
            adapter.send(result, plain_text, ai_advice, ticker_data)
            console.print(f"  [green]Email enviado a {config.email_to}[/green]")
        except Exception as e:
            console.print(f"  [red]Error al enviar email: {e}[/red]")
    else:
        console.print("  [dim]Email no configurado (completá .env para activarlo).[/dim]")

    console.print("[bold green]Análisis completado.[/bold green]")


def start_scheduler(config: Config) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        console.print("[red]APScheduler no instalado. Ejecutá: pip install apscheduler[/red]")
        sys.exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_analysis,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=config.run_hour,
            minute=config.run_minute,
            timezone=config.timezone,
        ),
        kwargs={"config": config},
        id="portfolio_analysis",
        misfire_grace_time=300,
        coalesce=True,
    )

    console.print(
        f"[bold green]Scheduler iniciado.[/bold green] "
        f"Próxima ejecución: lunes a viernes a las "
        f"[bold]{config.run_hour:02d}:{config.run_minute:02d} ART[/bold]"
    )
    console.print("[dim]Presioná Ctrl+C para detener.[/dim]")
    console.print("[dim]Usá 'python main.py --now' para ejecutar inmediatamente.[/dim]")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler detenido.[/yellow]")
        scheduler.shutdown()


def main() -> None:
    config = Config()
    args = set(sys.argv[1:])

    if "--now" in args:
        run_analysis(config, force=False)
    elif "--force" in args:
        run_analysis(config, force=True)
    else:
        start_scheduler(config)


if __name__ == "__main__":
    main()
