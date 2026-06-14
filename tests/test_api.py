def _activo_payload(ticker="AAPL"):
    return {"ticker": ticker, "nombre": "Apple Inc.", "tipo": "accion", "mercado": "NASDAQ"}


def test_listar_activos_vacio(client):
    resp = client.get("/activos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_crear_activo_devuelve_201_con_id(client):
    resp = client.post("/activos", json=_activo_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["ticker"] == "AAPL"
    assert body["mercado"] == "NASDAQ"


def test_listar_activos_devuelve_los_creados(client):
    client.post("/activos", json=_activo_payload("AAPL"))
    client.post("/activos", json=_activo_payload("MSFT"))
    resp = client.get("/activos")
    assert resp.status_code == 200
    tickers = {a["ticker"] for a in resp.json()}
    assert tickers == {"AAPL", "MSFT"}


def test_crear_activo_body_invalido_devuelve_400(client):
    resp = client.post("/activos", json={"ticker": "AAPL"})  # faltan campos
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_activo_enum_invalido_devuelve_400(client):
    payload = _activo_payload()
    payload["mercado"] = "LONDON"  # fuera del enum
    resp = client.post("/activos", json=payload)
    assert resp.status_code == 400
    assert "message" in resp.json()
