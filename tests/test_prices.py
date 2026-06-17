import os

import pandas as pd

from scripts import prices


def test_obtener_ohlc_lee_de_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "prices_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(prices, "CACHE_DIR", str(cache_dir))

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-03"], utc=True),
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [100, 200],
        }
    )
    df.to_csv(os.path.join(str(cache_dir), "AAPL_ohlc.csv"), index=False)

    ohlc, procedencia, fecha = prices.obtener_ohlc("AAPL")
    assert procedencia == "cache"
    assert list(ohlc.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(ohlc) == 2
    assert fecha == "2026-01-03"


def test_obtener_ohlc_sin_cache_ni_red_devuelve_none(tmp_path, monkeypatch):
    cache_dir = tmp_path / "prices_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(prices, "CACHE_DIR", str(cache_dir))

    def fail(_ticker):
        raise RuntimeError("sin red")

    monkeypatch.setattr(prices, "_ohlc_desde_red", fail)
    ohlc, procedencia, fecha = prices.obtener_ohlc("ZZZZ")
    assert ohlc is None and procedencia == "none" and fecha is None
