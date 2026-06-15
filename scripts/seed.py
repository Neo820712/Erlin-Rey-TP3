from datetime import datetime, timezone

from sqlmodel import Session, select

from backend.database import create_db, engine
from backend.models import Activo, Analisis
from scripts.indicators import analizar
from scripts.prices import obtener_precios

ACTIVOS = [
    {"ticker": "AAPL", "nombre": "Apple Inc.", "tipo": "accion", "mercado": "NASDAQ"},
    {"ticker": "GOOGL", "nombre": "Alphabet Inc.", "tipo": "accion", "mercado": "NASDAQ"},
    {"ticker": "MSFT", "nombre": "Microsoft Corp.", "tipo": "accion", "mercado": "NASDAQ"},
]

HARDCODE = {
    "AAPL": {"senal": "compra", "confianza": 0.67, "resumen": "RSI 45.0 (hold), MACD positivo (compra), SMA20 > SMA50 (compra) -> compra por mayoria"},
    "GOOGL": {"senal": "hold", "confianza": 0.33, "resumen": "RSI 55.0 (hold), MACD ~0 (hold), SMA20 ~ SMA50 (hold) -> hold"},
    "MSFT": {"senal": "venta", "confianza": 0.67, "resumen": "RSI 72.0 (venta), MACD negativo (venta), SMA20 < SMA50 (venta) -> venta por mayoria"},
}


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _analisis_de(ticker: str) -> dict:
    close, procedencia, _ = obtener_precios(ticker)
    if procedencia == "none":
        return HARDCODE[ticker]
    try:
        res = analizar(close)
    except ValueError:
        return HARDCODE[ticker]
    return {"senal": res["senal"], "confianza": res["confianza"], "resumen": res["resumen"]}


def seed() -> None:
    create_db()
    with Session(engine) as session:
        for datos in ACTIVOS:
            existe = session.exec(select(Activo).where(Activo.ticker == datos["ticker"])).first()
            if existe is not None:
                print(f"{datos['ticker']}: ya existe, se omite")
                continue
            activo = Activo(**datos)
            session.add(activo)
            session.commit()
            session.refresh(activo)

            a = _analisis_de(datos["ticker"])
            analisis = Analisis(
                activo_id=activo.id,
                tipo="tecnico",
                senal=a["senal"],
                confianza=a["confianza"],
                resumen=a["resumen"],
                created_at=_ahora_iso(),
            )
            session.add(analisis)
            session.commit()
            print(f"{datos['ticker']}: creado con analisis tecnico ({a['senal']})")


if __name__ == "__main__":
    seed()
