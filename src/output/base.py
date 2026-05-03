from abc import ABC, abstractmethod
from src.analyzer import PortfolioResult
from src.market_data import TickerData


class OutputAdapter(ABC):
    @abstractmethod
    def send(self, result: PortfolioResult, plain_text: str, ai_advice: str, ticker_data: dict[str, TickerData]) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
