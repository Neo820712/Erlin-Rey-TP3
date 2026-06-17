from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.models import MercadoCedear
from scripts import mercado


def _engine_memoria():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def test_fila_desde_arma_dict_completo():
    fila = mercado.fila_desde(
        entrada={"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc."},
        precio_usd=190.5, var_pct=1.23, volumen=42100000,
        rsi=44.1, senal="hold",
        info={"trailingPE": 28.4, "trailingEps": 6.43, "marketCap": 2800000000000,
              "fiftyTwoWeekHigh": 260.0, "fiftyTwoWeekLow": 164.0,
              "freeCashflow": 99000000000, "profitMargins": 0.25, "returnOnEquity": 1.5,
              "priceToBook": 47.3, "dividendYield": 0.005},
    )
    assert fila["ticker_byma"] == "AAPL"
    assert fila["pe"] == 28.4 and fila["market_cap"] == 2800000000000
    assert fila["w52_high"] == 260.0
    assert fila["free_cash_flow"] == 99000000000 and fila["margen_neto"] == 0.25
    assert fila["roe"] == 1.5 and fila["price_to_book"] == 47.3 and fila["dividend_yield"] == 0.005


def test_fila_desde_tolera_info_vacia():
    fila = mercado.fila_desde(
        entrada={"ticker_byma": "ZZZ", "ticker_us": "ZZZ", "nombre": "Z"},
        precio_usd=1.0, var_pct=0.0, volumen=1, rsi=50.0, senal="hold", info={},
    )
    assert fila["pe"] is None and fila["market_cap"] is None and fila["eps"] is None
    assert fila["free_cash_flow"] is None and fila["roe"] is None and fila["dividend_yield"] is None


def test_persistir_hace_upsert(monkeypatch):
    eng = _engine_memoria()
    monkeypatch.setattr(mercado, "engine", eng)

    filas_v1 = [{"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc.",
                 "precio_usd": 100.0, "var_pct": 1.0, "volumen": 10, "rsi": 50.0, "senal": "hold",
                 "pe": None, "eps": None, "market_cap": None, "w52_high": None, "w52_low": None}]
    mercado.persistir(filas_v1, "2026-06-15T12:00:00Z")

    filas_v2 = [{"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc.",
                 "precio_usd": 200.0, "var_pct": 2.0, "volumen": 20, "rsi": 60.0, "senal": "compra",
                 "pe": None, "eps": None, "market_cap": None, "w52_high": None, "w52_low": None}]
    mercado.persistir(filas_v2, "2026-06-15T13:00:00Z")

    with Session(eng) as s:
        todas = s.exec(select(MercadoCedear)).all()
        assert len(todas) == 1  # upsert, no duplica
        assert todas[0].precio_usd == 200.0
        assert todas[0].actualizado_en == "2026-06-15T13:00:00Z"


def _fila(ticker):
    return {"ticker_byma": ticker, "ticker_us": ticker, "nombre": f"{ticker} Inc.",
            "precio_usd": 1.0, "var_pct": 0.0, "volumen": 1, "rsi": 50.0, "senal": "hold",
            "pe": None, "eps": None, "market_cap": None, "w52_high": None, "w52_low": None}


def test_persistir_borra_tickers_que_salieron_del_catalogo(monkeypatch):
    eng = _engine_memoria()
    monkeypatch.setattr(mercado, "engine", eng)

    mercado.persistir([_fila("AAPL"), _fila("INTC")], "2026-06-15T12:00:00Z")
    mercado.persistir([_fila("AAPL"), _fila("UBER")], "2026-06-15T13:00:00Z")

    with Session(eng) as s:
        tickers = {m.ticker_byma for m in s.exec(select(MercadoCedear)).all()}
        assert tickers == {"AAPL", "UBER"}  # INTC fue removido


def test_datos_de_ticker_sin_senal_ni_rsi_y_con_ohlc(monkeypatch):
    import sys
    import types

    import pandas as pd

    fake = types.ModuleType("yfinance")
    idx = pd.date_range("2025-01-01", periods=60, freq="D", tz="UTC")
    df = pd.DataFrame(
        {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100}, index=idx
    )

    class FakeTk:
        def __init__(self, _t):
            pass

        def history(self, period="1y"):
            return df

        @property
        def info(self):
            return {"trailingPE": 10}

    fake.Ticker = FakeTk
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    r = mercado._datos_de_ticker({"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple"})
    assert r["fila"]["rsi"] is None and r["fila"]["senal"] is None
    assert len(r["precios"]) == 60
    assert r["precios"][0]["ticker"] == "AAPL"
