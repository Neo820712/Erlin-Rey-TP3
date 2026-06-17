import pandas as pd

from scripts.indicators import analizar, macd, rsi, sma


def test_sma_calcula_promedio_movil():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 3).iloc[-1] == 4.0


def test_rsi_sube_con_tendencia_alcista():
    s = pd.Series(range(1, 60), dtype=float)
    assert rsi(s, 14).iloc[-1] > 70


def test_rsi_baja_con_tendencia_bajista():
    s = pd.Series(range(60, 1, -1), dtype=float)
    assert rsi(s, 14).iloc[-1] < 30


def test_macd_linea_sobre_senal_en_tendencia_alcista():
    s = pd.Series(range(1, 60), dtype=float)
    macd_line, signal_line = macd(s)
    assert macd_line.iloc[-1] > signal_line.iloc[-1]


def test_score_rsi_buckets():
    from scripts.indicators import _score_rsi
    assert _score_rsi(20) == 90
    assert _score_rsi(40) == 100
    assert _score_rsi(50) == 70
    assert _score_rsi(60) == 45
    assert _score_rsi(68) == 25
    assert _score_rsi(80) == 5


def test_score_tendencia():
    from scripts.indicators import _score_tendencia
    assert _score_tendencia(110, 105, 100) == 100
    assert _score_tendencia(90, 95, 100) == 0
    assert _score_tendencia(110, 95, 100) == 50


def test_score_macd():
    from scripts.indicators import _score_macd
    assert _score_macd(1.0, 0.5) == 100   # crece (+30) y >0 (+20)
    assert _score_macd(-0.5, -0.2) == 35  # baja (-15), <0
    assert _score_macd(0.5, 0.5) == 70    # plano, >0 (+20)


def test_senal_desde_score():
    from scripts.indicators import _senal_desde_score
    assert _senal_desde_score(70) == "compra"
    assert _senal_desde_score(50) == "hold"
    assert _senal_desde_score(20) == "venta"


def test_confianza_desde_score():
    from scripts.indicators import _confianza_desde_score
    assert _confianza_desde_score(50) == 0.0
    assert _confianza_desde_score(100) == 1.0
    assert _confianza_desde_score(10) == 0.8


def test_analizar_incluye_score_y_coherencia():
    s = pd.Series(range(1, 80), dtype=float)
    r = analizar(s)
    assert 0 <= r["score"] <= 100
    assert r["senal"] in {"compra", "venta", "hold"}
    assert r["confianza"] == round(abs(r["score"] - 50) * 2 / 100, 2)
    assert "Score" in r["resumen"]
    for k in ("rsi", "macd", "signal", "sma20", "sma50"):
        assert k in r


def test_analizar_serie_corta_falla():
    import pytest
    s = pd.Series(range(1, 30), dtype=float)
    with pytest.raises(ValueError):
        analizar(s)
