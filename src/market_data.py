from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import yfinance as yf


@dataclass
class PriceData:
    ticker: str
    prev_close: float
    current_close: float
    change_pct: float
    change_abs: float
    currency: str
    available: bool = True


@dataclass
class NewsItem:
    title: str
    publisher: str
    published_utc: str
    url: str
    summary: Optional[str] = None


@dataclass
class TickerData:
    price: Optional[PriceData]
    news: list = field(default_factory=list)


def _parse_news(raw_news: list, max_items: int, cutoff_hours: int = 36) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cutoff_hours)
    result = []
    for item in raw_news:
        ts = item.get("providerPublishTime", 0)
        pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if pub_dt < cutoff:
            continue
        result.append(NewsItem(
            title=item.get("title", ""),
            publisher=item.get("publisher", ""),
            published_utc=pub_dt.strftime("%Y-%m-%d %H:%M UTC"),
            url=item.get("link", ""),
            summary=item.get("summary"),
        ))
        if len(result) >= max_items:
            break
    return result


def fetch_all_tickers(tickers: list[str], news_max_items: int = 3) -> dict[str, TickerData]:
    result: dict[str, TickerData] = {}

    # Batch price fetch
    ticker_str = " ".join(tickers)
    try:
        df = yf.download(
            ticker_str,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"[WARNING] yfinance batch download failed: {e}")
        df = None

    for ticker in tickers:
        price_data: Optional[PriceData] = None

        if df is not None and not df.empty:
            try:
                # Single ticker download gives flat columns; multi-ticker gives MultiIndex
                if len(tickers) == 1:
                    close_series = df["Close"]
                else:
                    close_series = df["Close"][ticker]

                close_series = close_series.dropna()
                if len(close_series) >= 2:
                    prev = float(close_series.iloc[-2])
                    curr = float(close_series.iloc[-1])
                    change_pct = (curr - prev) / prev * 100
                    currency = "ARS" if ticker.endswith(".BA") else "USD"
                    price_data = PriceData(
                        ticker=ticker,
                        prev_close=prev,
                        current_close=curr,
                        change_pct=change_pct,
                        change_abs=curr - prev,
                        currency=currency,
                    )
            except Exception as e:
                print(f"[WARNING] Could not parse price for {ticker}: {e}")

        if price_data is None:
            price_data = PriceData(
                ticker=ticker,
                prev_close=0.0,
                current_close=0.0,
                change_pct=0.0,
                change_abs=0.0,
                currency="USD",
                available=False,
            )

        # Per-ticker news
        news_items: list[NewsItem] = []
        try:
            t = yf.Ticker(ticker)
            raw = t.news or []
            news_items = _parse_news(raw, max_items=news_max_items)
        except Exception as e:
            print(f"[WARNING] Could not fetch news for {ticker}: {e}")

        result[ticker] = TickerData(price=price_data, news=news_items)

    return result
