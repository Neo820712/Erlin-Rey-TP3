import json
import subprocess


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
    assert fila.free_cash_flow is None and fila.margen_neto is None and fila.roe is None
    assert fila.price_to_book is None and fila.dividend_yield is None


def _sembrar_fila(session, ticker="AAPL", actualizado="2026-06-15T12:00:00Z"):
    from backend.models import MercadoCedear
    fila = MercadoCedear(
        ticker_byma=ticker, ticker_us=ticker, nombre=f"{ticker} Inc.",
        precio_usd=100.0, var_pct=1.0, volumen=1000, rsi=50.0, senal="hold",
        actualizado_en=actualizado,
    )
    session.add(fila)
    session.commit()
    return fila


def test_get_catalogo_lee_el_archivo(client, tmp_path, monkeypatch):
    import backend.main as main
    catalogo = tmp_path / "cedears.json"
    catalogo.write_text(
        json.dumps([
            {"ticker_byma": "AAPL", "ticker_us": "AAPL", "nombre": "Apple Inc.",
             "mercado": "NASDAQ", "tipo": "accion"}
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "_CATALOGO_PATH", str(catalogo))
    resp = client.get("/mercado/catalogo")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["ticker_byma"] == "AAPL"
    assert body[0]["mercado"] == "NASDAQ"


def test_get_catalogo_archivo_faltante_devuelve_500(client, monkeypatch):
    import backend.main as main
    monkeypatch.setattr(main, "_CATALOGO_PATH", "data/no-existe-cedears.json")
    resp = client.get("/mercado/catalogo")
    assert resp.status_code == 500
    assert "message" in resp.json()


def test_get_mercado_vacio(client):
    resp = client.get("/mercado/cedears")
    assert resp.status_code == 200
    assert resp.json() == {"cedears": [], "actualizado_en": None}


def test_get_mercado_con_filas(client, session):
    _sembrar_fila(session, "AAPL")
    _sembrar_fila(session, "MSFT")
    resp = client.get("/mercado/cedears")
    assert resp.status_code == 200
    body = resp.json()
    assert {c["ticker_byma"] for c in body["cedears"]} == {"AAPL", "MSFT"}
    assert body["actualizado_en"] == "2026-06-15T12:00:00Z"


def test_get_fundamentales_devuelve_la_fila(client, session):
    _sembrar_fila(session, "AAPL")
    resp = client.get("/mercado/AAPL/fundamentales")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker_byma"] == "AAPL"
    assert "free_cash_flow" in body and "roe" in body and "dividend_yield" in body


def test_get_fundamentales_inexistente_devuelve_404(client):
    resp = client.get("/mercado/ZZZZ/fundamentales")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_post_actualizar_devuelve_resumen(client, monkeypatch):
    salida = json.dumps({"actualizados": 30, "actualizado_en": "2026-06-15T12:00:00Z"})

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=salida, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post("/mercado/actualizar")
    assert resp.status_code == 200
    assert resp.json() == {"actualizados": 30, "actualizado_en": "2026-06-15T12:00:00Z"}


def test_post_actualizar_falla_devuelve_500(client, monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post("/mercado/actualizar")
    assert resp.status_code == 500
    assert "message" in resp.json()


def test_get_historico_passthrough(client, monkeypatch):
    payload = {
        "ohlc": [{"time": "2026-01-02", "open": 1, "high": 2, "low": 0.5, "close": 1.5}],
        "series": {"sma20": [None], "sma50": [None], "rsi": [None], "macd": [None], "signal": [None], "hist": [None]},
        "indicadores": {"rsi": 44.1, "macd": 2.3, "signal": 5.8, "sma20": 1.0, "sma50": 1.0, "senal": "hold", "confianza": 0.33},
    }

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.get("/mercado/AAPL/historico?periodo=3m")
    assert resp.status_code == 200
    assert resp.json() == payload


def test_get_historico_periodo_invalido_devuelve_400(client):
    resp = client.get("/mercado/AAPL/historico?periodo=5x")
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_get_historico_ticker_invalido_devuelve_400(client):
    # un ticker que empieza con '-' no debe poder colarse como flag al subproceso
    resp = client.get("/mercado/-rf/historico?periodo=3m")
    assert resp.status_code == 400
    assert "message" in resp.json()
