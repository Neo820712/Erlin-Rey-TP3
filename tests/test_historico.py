import json
import numpy as np
import pandas as pd

from scripts.historico import _ventana_dias, construir_historico


def _df_sintetico(n=120):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close - 1, "High": close + 1, "Low": close - 2, "Close": close, "Volume": 1000},
        index=idx,
    )


def test_ventana_dias_mapea_periodos():
    assert _ventana_dias("1m") == 22
    assert _ventana_dias("3m") == 66
    assert _ventana_dias("6m") == 126
    assert _ventana_dias("1y") == 252


def test_construir_historico_recorta_a_la_ventana():
    df = _df_sintetico(120)
    out = construir_historico(df, "1m")
    assert len(out["ohlc"]) == 22
    assert len(out["series"]["sma20"]) == 22
    assert set(out["ohlc"][0].keys()) == {"time", "open", "high", "low", "close"}


def test_construir_historico_indicadores_finales():
    df = _df_sintetico(120)
    out = construir_historico(df, "3m")
    ind = out["indicadores"]
    assert ind["senal"] in {"compra", "venta", "hold"}
    assert ind["sma20"] is not None and ind["sma50"] is not None


def test_main_sin_precios_devuelve_0_con_error(monkeypatch, capsys):
    import scripts.historico as h

    monkeypatch.setattr(h, "obtener_ohlc", lambda t, p="1y": (None, "none", None))
    rc = h.main(["historico.py", "AAPL", "3m"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "error" in out
    assert "AAPL" in out["error"]


def test_main_lee_de_obtener_ohlc_y_sin_score_en_indicadores(monkeypatch, capsys):
    import scripts.historico as h

    df = _df_sintetico(120)
    monkeypatch.setattr(h, "obtener_ohlc", lambda t, p="1y": (df, "db", "2025-04-30"))
    rc = h.main(["historico.py", "AAPL", "3m"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "ohlc" in out and "indicadores" in out
    assert "score" not in out["indicadores"]
    assert out["indicadores"]["senal"] in {"compra", "venta", "hold"}
