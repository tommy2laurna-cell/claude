from dataclasses import dataclass
import requests

FALLBACK_CCL_RATE = 1300.0  # update periodically if all sources fail


@dataclass
class FXRate:
    usd_ars: float
    source: str


def _fetch_dolarapi() -> float:
    r = requests.get(
        "https://dolarapi.com/v1/dolares/contadoconliqui",
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    return (data["compra"] + data["venta"]) / 2


def _fetch_bluelytics() -> float:
    r = requests.get("https://api.bluelytics.com.ar/v2/latest", timeout=5)
    r.raise_for_status()
    data = r.json()
    blue = data["blue"]
    return (blue["value_buy"] + blue["value_sell"]) / 2


def fetch_ccl_rate() -> FXRate:
    for fetcher, name in [(_fetch_dolarapi, "dolarapi.com"), (_fetch_bluelytics, "bluelytics.com.ar")]:
        try:
            rate = fetcher()
            return FXRate(usd_ars=rate, source=name)
        except Exception:
            continue

    return FXRate(usd_ars=FALLBACK_CCL_RATE, source="fallback-hardcoded (actualizar en fx_rate.py)")
