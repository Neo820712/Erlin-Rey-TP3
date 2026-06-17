import numpy as np
import pandas as pd
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from scripts import prices


def _engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def _df(n=60):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close - 1, "High": close + 1, "Low": close - 2, "Close": close, "Volume": 1000},
        index=idx,
    )


def test_filas_precio_desde_df():
    filas = prices.filas_precio_desde_df("aapl", _df(3))
    assert len(filas) == 3
    assert filas[0]["ticker"] == "AAPL"
    assert set(filas[0].keys()) == {"ticker", "fecha", "open", "high", "low", "close", "volumen"}
    assert filas[0]["volumen"] == 1000


def test_guardar_y_obtener_ohlc_roundtrip():
    eng = _engine()
    filas = prices.filas_precio_desde_df("AAPL", _df(60))
    n = prices.guardar_ohlc(filas, eng=eng)
    assert n == 60
    df, procedencia, fecha = prices.obtener_ohlc("AAPL", eng=eng)
    assert procedencia == "db"
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(df) == 60
    assert fecha == "2025-03-01"  # 60 dias desde 2025-01-01


def test_guardar_ohlc_reescribe_todo():
    eng = _engine()
    prices.guardar_ohlc(prices.filas_precio_desde_df("AAPL", _df(60)), eng=eng)
    prices.guardar_ohlc(prices.filas_precio_desde_df("MSFT", _df(60)), eng=eng)
    df_aapl, proc_aapl, _ = prices.obtener_ohlc("AAPL", eng=eng)
    assert proc_aapl == "none"  # el segundo guardar reescribio todo
    df_msft, proc_msft, _ = prices.obtener_ohlc("MSFT", eng=eng)
    assert proc_msft == "db"


def test_obtener_ohlc_sin_datos_devuelve_none():
    eng = _engine()
    df, procedencia, fecha = prices.obtener_ohlc("ZZZZ", eng=eng)
    assert df is None and procedencia == "none" and fecha is None
