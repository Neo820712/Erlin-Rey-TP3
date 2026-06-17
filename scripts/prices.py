import pandas as pd
from sqlmodel import Session, SQLModel, select

from backend.database import engine
from backend.models import Precio

_OHLC_COLS = ["Open", "High", "Low", "Close", "Volume"]


def filas_precio_desde_df(ticker: str, df: pd.DataFrame) -> list[dict]:
    """Convierte un DataFrame OHLCV (indexado por fecha) en filas para la tabla precios.
    Descarta las filas con algun OHLC nulo: yfinance devuelve NaN en fechas sin dato y
    las columnas open/high/low/close son NOT NULL."""
    filas = []
    for fecha, row in df.iterrows():
        if row[["Open", "High", "Low", "Close"]].isna().any():
            continue
        vol = row["Volume"]
        filas.append(
            {
                "ticker": ticker.upper(),
                "fecha": fecha.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volumen": None if pd.isna(vol) else int(vol),
            }
        )
    return filas


def guardar_ohlc(filas: list[dict], eng=engine) -> int:
    """Reescribe la tabla precios completa: la descarta, la recrea e inserta las filas dadas.
    Mismo patron de snapshot que mercado.persistir. Devuelve cuantas filas escribio."""
    Precio.__table__.drop(eng, checkfirst=True)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        for f in filas:
            session.add(Precio(**f))
        session.commit()
    return len(filas)


def obtener_ohlc(ticker: str, periodo: str = "1y", eng=engine):
    """Devuelve (df_ohlcv, procedencia, fecha) leyendo de la tabla precios.
    procedencia 'db' si hay filas, 'none' si no. `periodo` se reserva para el recorte en el llamador."""
    with Session(eng) as session:
        filas = session.exec(
            select(Precio).where(Precio.ticker == ticker.upper()).order_by(Precio.fecha)
        ).all()
    if not filas:
        return None, "none", None
    df = pd.DataFrame(
        {
            "Open": [f.open for f in filas],
            "High": [f.high for f in filas],
            "Low": [f.low for f in filas],
            "Close": [f.close for f in filas],
            "Volume": [f.volumen for f in filas],
        },
        index=pd.to_datetime([f.fecha for f in filas], utc=True),
    )
    df.index.name = "Date"
    return df[_OHLC_COLS], "db", filas[-1].fecha
