from collections import Counter

import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def _voto_rsi(valor: float) -> str:
    if valor < 30:
        return "compra"
    if valor > 70:
        return "venta"
    return "hold"


def _voto_macd(macd_val: float, signal_val: float) -> str:
    if macd_val > signal_val:
        return "compra"
    if macd_val < signal_val:
        return "venta"
    return "hold"


def _voto_sma(sma_corta: float, sma_larga: float) -> str:
    if sma_corta > sma_larga:
        return "compra"
    if sma_corta < sma_larga:
        return "venta"
    return "hold"


def _voto_mayoria(votos: list[str]) -> tuple[str, float]:
    conteo = Counter(votos)
    senal, n = conteo.most_common(1)[0]
    if n == 1:  # los tres votan distinto: sin mayoria
        return "hold", 0.33
    return senal, round(n / 3, 2)


def analizar(close: pd.Series) -> dict:
    rsi_val = float(rsi(close).iloc[-1])
    macd_line, signal_line = macd(close)
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    sma20 = float(sma(close, 20).iloc[-1])
    sma50 = float(sma(close, 50).iloc[-1])

    v_rsi = _voto_rsi(rsi_val)
    v_macd = _voto_macd(macd_val, signal_val)
    v_sma = _voto_sma(sma20, sma50)
    senal, confianza = _voto_mayoria([v_rsi, v_macd, v_sma])

    rel = ">" if sma20 > sma50 else "<" if sma20 < sma50 else "="
    resumen = (
        f"RSI {rsi_val:.1f} ({v_rsi}), "
        f"MACD {macd_val:.2f} vs senal {signal_val:.2f} ({v_macd}), "
        f"SMA20 {sma20:.2f} {rel} SMA50 {sma50:.2f} ({v_sma}) "
        f"-> {senal} por mayoria"
    )
    return {
        "senal": senal,
        "confianza": confianza,
        "resumen": resumen,
        "rsi": rsi_val,
        "macd": macd_val,
        "signal": signal_val,
        "sma20": sma20,
        "sma50": sma50,
    }
