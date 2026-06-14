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


def _crear_activo(client, ticker="AAPL"):
    return client.post("/activos", json=_activo_payload(ticker)).json()["id"]


def _analisis_payload(tipo="tecnico", senal="compra", confianza=0.67, resumen="ok"):
    return {"tipo": tipo, "senal": senal, "confianza": confianza, "resumen": resumen}


def test_detalle_activo_sin_analisis(client):
    aid = _crear_activo(client)
    resp = client.get(f"/activos/{aid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == aid
    assert body["senales_recientes"] == {"tecnico": None, "sentimiento": None}


def test_detalle_activo_toma_la_senal_mas_reciente_por_tipo(client):
    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "venta"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("sentimiento", "hold"))
    resp = client.get(f"/activos/{aid}")
    assert resp.status_code == 200
    sr = resp.json()["senales_recientes"]
    assert sr["tecnico"] == "venta"
    assert sr["sentimiento"] == "hold"


def test_detalle_activo_inexistente_devuelve_404(client):
    resp = client.get("/activos/999")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_activo_devuelve_204(client):
    aid = _crear_activo(client)
    resp = client.delete(f"/activos/{aid}")
    assert resp.status_code == 204
    assert client.get(f"/activos/{aid}").status_code == 404


def test_borrar_activo_inexistente_devuelve_404(client):
    resp = client.delete("/activos/999")
    assert resp.status_code == 404
    assert "message" in resp.json()
