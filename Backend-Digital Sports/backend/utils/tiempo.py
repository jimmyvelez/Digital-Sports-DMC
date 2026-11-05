from datetime import datetime


def ahora():
    """Fecha y hora local sin zona horaria (la institución opera en una sola zona)."""
    return datetime.now().replace(microsecond=0)


def iso(valor):
    """Serializa un datetime/date a ISO 8601 o devuelve None."""
    return valor.isoformat() if valor else None
