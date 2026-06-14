import pandas as pd

from scripts.indicators import analizar, macd, rsi, sma


def test_sma_calcula_promedio_movil():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 3).iloc[-1] == 4.0  # (3+4+5)/3


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


def test_analizar_mayoria_da_estructura_valida():
    s = pd.Series(range(1, 80), dtype=float)
    r = analizar(s)
    assert r["senal"] in {"compra", "venta", "hold"}
    assert r["confianza"] in {0.33, 0.67, 1.0}
    assert isinstance(r["resumen"], str) and r["resumen"]


def test_voto_mayoria_empate_a_tres_da_hold_033():
    from scripts.indicators import _voto_mayoria
    senal, confianza = _voto_mayoria(["compra", "venta", "hold"])
    assert senal == "hold"
    assert confianza == 0.33


def test_voto_mayoria_unanimidad_da_confianza_uno():
    from scripts.indicators import _voto_mayoria
    senal, confianza = _voto_mayoria(["compra", "compra", "compra"])
    assert senal == "compra"
    assert confianza == 1.0


def test_voto_mayoria_dos_tercios():
    from scripts.indicators import _voto_mayoria
    senal, confianza = _voto_mayoria(["venta", "venta", "compra"])
    assert senal == "venta"
    assert confianza == 0.67
