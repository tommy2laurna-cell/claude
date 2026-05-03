import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.output.base import OutputAdapter
from src.analyzer import PortfolioResult
from src.market_data import TickerData
from src.config import Config
from src.report import build_html_email


class EmailAdapter(OutputAdapter):
    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return "Email"

    def send(self, result: PortfolioResult, plain_text: str, ai_advice: str, ticker_data: dict[str, TickerData]) -> bool:
        cfg = self.config
        subject = f"Portfolio CEDEAR — {result.timestamp}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg.email_from
        msg["To"] = cfg.email_to

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(build_html_email(result, ai_advice, ticker_data), "html", "utf-8"))

        with smtplib.SMTP(cfg.email_smtp_host, cfg.email_smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg.email_from, cfg.email_password)
            server.sendmail(cfg.email_from, cfg.email_to, msg.as_string())

        return True
