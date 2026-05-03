from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime

ART = ZoneInfo("America/Argentina/Buenos_Aires")

# Fixed + moveable Argentine holidays for 2026
# Format: (month, day)
HOLIDAYS_2026: set[tuple[int, int]] = {
    (1, 1),   # Año Nuevo
    (2, 16),  # Carnaval
    (2, 17),  # Carnaval
    (3, 24),  # Día Nacional de la Memoria
    (4, 2),   # Día del Veterano y de los Caídos en la Guerra de Malvinas
    (4, 3),   # Viernes Santo
    (5, 1),   # Día del Trabajador
    (5, 25),  # Revolución de Mayo
    (6, 15),  # Paso a la Inmortalidad del Gral. Güemes
    (6, 20),  # Paso a la Inmortalidad del Gral. Belgrano
    (7, 9),   # Día de la Independencia
    (8, 17),  # Paso a la Inmortalidad del Gral. San Martín
    (10, 12), # Día del Respeto a la Diversidad Cultural
    (11, 23), # Día de la Soberanía Nacional
    (12, 8),  # Inmaculada Concepción de María
    (12, 25), # Navidad
}

HOLIDAYS_BY_YEAR: dict[int, set[tuple[int, int]]] = {
    2026: HOLIDAYS_2026,
}


def is_business_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    holidays = HOLIDAYS_BY_YEAR.get(d.year, set())
    return (d.month, d.day) not in holidays


def today_art() -> date:
    return datetime.now(ART).date()


def should_run_today() -> bool:
    return is_business_day(today_art())
