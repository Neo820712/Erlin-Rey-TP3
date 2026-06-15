def test_mercado_cedear_roundtrip(session):
    from backend.models import MercadoCedear

    fila = MercadoCedear(
        ticker_byma="AAPL", ticker_us="AAPL", nombre="Apple Inc.",
        precio_usd=190.5, var_pct=1.23, volumen=42100000,
        rsi=44.1, senal="hold",
        pe=28.4, eps=6.43, market_cap=2800000000000,
        w52_high=260.0, w52_low=164.0,
        actualizado_en="2026-06-15T12:00:00Z",
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    assert fila.id is not None
    assert fila.senal == "hold"


def test_mercado_cedear_fundamentales_opcionales(session):
    from backend.models import MercadoCedear

    fila = MercadoCedear(
        ticker_byma="ZZZ", ticker_us="ZZZ", nombre="Sin fundamentales",
        precio_usd=10.0, var_pct=0.0, volumen=100, rsi=50.0, senal="hold",
        actualizado_en="2026-06-15T12:00:00Z",
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    assert fila.pe is None and fila.market_cap is None and fila.w52_high is None
