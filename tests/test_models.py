from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.models import Analisis, Precio, SenalesRecientes


def _engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


def test_analisis_guarda_score():
    eng = _engine()
    with Session(eng) as s:
        a = Analisis(activo_id=1, tipo="tecnico", senal="compra", confianza=0.6,
                     resumen="x", score=80.0, created_at="2026-06-17T00:00:00Z")
        s.add(a); s.commit(); s.refresh(a)
        assert a.id is not None and a.score == 80.0


def test_analisis_score_es_opcional():
    a = Analisis(activo_id=1, tipo="tecnico", senal="hold", confianza=0.0,
                 resumen="x", created_at="2026-06-17T00:00:00Z")
    assert a.score is None


def test_senales_recientes_tiene_score():
    sr = SenalesRecientes()
    assert sr.score is None


def test_precio_roundtrip():
    eng = _engine()
    with Session(eng) as s:
        s.add(Precio(ticker="AAPL", fecha="2026-01-02", open=1.0, high=2.0, low=0.5,
                     close=1.5, volumen=100))
        s.commit()
        filas = s.exec(select(Precio).where(Precio.ticker == "AAPL")).all()
        assert len(filas) == 1 and filas[0].close == 1.5 and filas[0].volumen == 100
