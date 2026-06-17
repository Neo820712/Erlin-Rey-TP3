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


def _score_rsi(rsi_val: float) -> float:
    if rsi_val <= 30:
        return 90.0
    if rsi_val <= 45:
        return 100.0
    if rsi_val <= 55:
        return 70.0
    if rsi_val <= 65:
        return 45.0
    if rsi_val <= 70:
        return 25.0
    return 5.0


def _score_tendencia(precio: float, sma20: float, sma50: float) -> float:
    s = 0.0
    if precio > sma50:
        s += 50.0
    if sma20 > sma50:
        s += 50.0
    return s


def _score_macd(hist_actual: float, hist_previo: float) -> float:
    s = 50.0
    if hist_actual > hist_previo:
        s += 30.0
    elif hist_actual < hist_previo:
        s -= 15.0
    if hist_actual > 0:
        s += 20.0
    return max(0.0, min(100.0, s))


def _senal_desde_score(score: float) -> str:
    if score >= 66:
        return "compra"
    if score < 33:
        return "venta"
    return "hold"


def _confianza_desde_score(score: float) -> float:
    return round(abs(score - 50) * 2 / 100, 2)


def analizar(close: pd.Series) -> dict:
    close = close.dropna()
    if len(close) < 50:
        raise ValueError(
            f"serie de precios insuficiente: {len(close)} cierres (se requieren >= 50 para SMA50)"
        )
    rsi_val = float(rsi(close).iloc[-1])
    macd_line, signal_line = macd(close)
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    hist = macd_line - signal_line
    hist_actual = float(hist.iloc[-1])
    hist_previo = float(hist.iloc[-2])
    sma20 = float(sma(close, 20).iloc[-1])
    sma50 = float(sma(close, 50).iloc[-1])
    precio = float(close.iloc[-1])

    s_rsi = _score_rsi(rsi_val)
    s_tend = _score_tendencia(precio, sma20, sma50)
    s_macd = _score_macd(hist_actual, hist_previo)
    score = round(0.40 * s_rsi + 0.30 * s_tend + 0.30 * s_macd, 1)
    senal = _senal_desde_score(score)
    confianza = _confianza_desde_score(score)

    tend_txt = "alcista" if s_tend >= 100 else "mixta" if s_tend == 50 else "bajista"
    hist_dir = "creciente" if hist_actual > hist_previo else "decreciente" if hist_actual < hist_previo else "plano"
    resumen = (
        f"Score {score:.0f}/100 ({senal}). "
        f"RSI {rsi_val:.1f} [{s_rsi:.0f}], "
        f"Tendencia {tend_txt} [{s_tend:.0f}], "
        f"MACD hist {hist_actual:+.2f} {hist_dir} [{s_macd:.0f}]"
    )
    return {
        "senal": senal,
        "confianza": confianza,
        "score": score,
        "resumen": resumen,
        "rsi": rsi_val,
        "macd": macd_val,
        "signal": signal_val,
        "sma20": sma20,
        "sma50": sma50,
    }
