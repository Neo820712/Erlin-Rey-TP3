import json

import numpy as np
import pandas as pd
import pytest

import scripts.score_tecnico as st


def _df(n=80):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n), index=idx)
    return pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1}, index=idx
    )


def test_computar_devuelve_las_cuatro_claves(monkeypatch):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (_df(), "db", "x"))
    r = st.computar("AAPL")
    assert set(r) == {"senal", "confianza", "resumen", "score"}
    assert 0 <= r["score"] <= 100


def test_computar_sin_precios_levanta(monkeypatch):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (None, "none", None))
    with pytest.raises(ValueError):
        st.computar("ZZZ")


def test_main_sin_precios_imprime_error_rc0(monkeypatch, capsys):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (None, "none", None))
    rc = st.main(["score_tecnico.py", "ZZZ"])
    assert rc == 0
    assert "error" in json.loads(capsys.readouterr().out)


def test_main_ok_imprime_json(monkeypatch, capsys):
    monkeypatch.setattr(st, "obtener_ohlc", lambda t, p="1y": (_df(), "db", "x"))
    rc = st.main(["score_tecnico.py", "AAPL"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "score" in out and out["senal"] in {"compra", "venta", "hold"}
