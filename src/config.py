import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: os.environ["ANTHROPIC_API_KEY"])
    claude_model: str = "claude-sonnet-4-6"

    portfolio_path: Path = field(default_factory=lambda: Path("portfolio.json"))

    news_max_items: int = 3

    # Email
    email_smtp_host: str = field(default_factory=lambda: os.getenv("EMAIL_SMTP_HOST", ""))
    email_smtp_port: int = field(default_factory=lambda: int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", ""))
    email_to: str = field(default_factory=lambda: os.getenv("EMAIL_TO", ""))
    email_password: str = field(default_factory=lambda: os.getenv("EMAIL_PASSWORD", ""))

    @property
    def email_configured(self) -> bool:
        return bool(self.email_smtp_host and self.email_from and self.email_to and self.email_password)
