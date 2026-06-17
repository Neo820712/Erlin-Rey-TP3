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


def test_crear_activo_ticker_duplicado_es_idempotente(client):
    primero = client.post("/activos", json=_activo_payload("AAPL"))
    assert primero.status_code == 201
    segundo = client.post("/activos", json=_activo_payload("AAPL"))
    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero.json()["id"]
    assert len(client.get("/activos").json()) == 1


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
    assert body["senales_recientes"] == {"tecnico": None, "sentimiento": None, "score": None}


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


def test_crear_analisis_devuelve_201(client):
    aid = _crear_activo(client)
    resp = client.post(f"/activos/{aid}/analisis", json=_analisis_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["activo_id"] == aid
    assert body["created_at"]
    assert body["senal"] == "compra"


def test_listar_analisis_orden_descendente(client):
    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "venta"))
    resp = client.get(f"/activos/{aid}/analisis")
    assert resp.status_code == 200
    senales = [a["senal"] for a in resp.json()]
    assert senales == ["venta", "compra"]


def test_crear_analisis_confianza_fuera_de_rango_devuelve_400(client):
    aid = _crear_activo(client)
    resp = client.post(f"/activos/{aid}/analisis", json=_analisis_payload(confianza=1.5))
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_analisis_en_activo_inexistente_devuelve_404(client):
    resp = client.post("/activos/999/analisis", json=_analisis_payload())
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_listar_analisis_de_activo_inexistente_devuelve_404(client):
    resp = client.get("/activos/999/analisis")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_analisis_devuelve_204(client):
    aid = _crear_activo(client)
    anid = client.post(f"/activos/{aid}/analisis", json=_analisis_payload()).json()["id"]
    resp = client.delete(f"/activos/{aid}/analisis/{anid}")
    assert resp.status_code == 204
    assert client.get(f"/activos/{aid}/analisis").json() == []


def test_borrar_analisis_inexistente_devuelve_404(client):
    aid = _crear_activo(client)
    resp = client.delete(f"/activos/{aid}/analisis/999")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_analisis_de_activo_inexistente_devuelve_404(client):
    resp = client.delete("/activos/999/analisis/1")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_borrar_activo_borra_sus_analisis_en_cascada(client, session):
    from sqlmodel import select
    from backend.models import Analisis

    aid = _crear_activo(client)
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("tecnico", "compra"))
    client.post(f"/activos/{aid}/analisis", json=_analisis_payload("sentimiento", "hold"))

    assert len(session.exec(select(Analisis).where(Analisis.activo_id == aid)).all()) == 2

    assert client.delete(f"/activos/{aid}").status_code == 204

    session.expire_all()
    assert session.exec(select(Analisis).where(Analisis.activo_id == aid)).all() == []


def test_detalle_activo_incluye_score(client):
    aid = _crear_activo(client)
    client.post(
        f"/activos/{aid}/analisis",
        json={"tipo": "tecnico", "senal": "compra", "confianza": 0.6, "resumen": "x", "score": 72.0},
    )
    sr = client.get(f"/activos/{aid}").json()["senales_recientes"]
    assert sr["tecnico"] == "compra" and sr["score"] == 72.0


def test_crear_analisis_tecnico_persiste_201(client, monkeypatch):
    import json
    import subprocess

    aid = _crear_activo(client)
    salida = json.dumps(
        {"senal": "compra", "confianza": 0.8, "resumen": "Score 90/100 (compra).", "score": 90.0}
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=salida, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post(f"/activos/{aid}/analisis/tecnico")
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "tecnico" and body["senal"] == "compra" and body["score"] == 90.0
    assert body["activo_id"] == aid and body["created_at"]


def test_crear_analisis_tecnico_sin_precios_devuelve_400(client, monkeypatch):
    import json
    import subprocess

    aid = _crear_activo(client)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout=json.dumps({"error": "sin precios para AAPL"}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    resp = client.post(f"/activos/{aid}/analisis/tecnico")
    assert resp.status_code == 400
    assert "message" in resp.json()


def test_crear_analisis_tecnico_activo_inexistente_devuelve_404(client):
    resp = client.post("/activos/999/analisis/tecnico")
    assert resp.status_code == 404
    assert "message" in resp.json()


def test_ruta_inexistente_usa_el_schema_de_error_unico(client):
    resp = client.get("/ruta-que-no-existe")
    assert resp.status_code == 404
    assert "message" in resp.json()
    assert "detail" not in resp.json()
