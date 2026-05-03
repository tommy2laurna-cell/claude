from src.output.base import OutputAdapter
from src.analyzer import PortfolioResult
from src.market_data import TickerData


class TerminalAdapter(OutputAdapter):
    def send(self, result: PortfolioResult, plain_text: str, ai_advice: str, ticker_data: dict[str, TickerData]) -> bool:
        # Rendering already happened in main.py via report.render_terminal()
        return True

    @property
    def name(self) -> str:
        return "Terminal"
