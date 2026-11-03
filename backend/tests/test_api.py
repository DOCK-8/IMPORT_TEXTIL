"""Pruebas funcionales de la API sobre la base cargada por el pipeline (se omiten si está vacía)."""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from dss.api.main import app
from dss.db import engine, sesion
from dss.models import IndiceViabilidad


def _hay_datos() -> bool:
    if not inspect(engine).has_table("indice_viabilidad"):
        return False
    with sesion() as s:
        return s.scalar(select(func.count()).select_from(IndiceViabilidad)) > 0


pytestmark = pytest.mark.skipif(not _hay_datos(), reason="Ejecute primero: python -m dss.pipeline")
cliente = TestClient(app)


def test_salud():
    assert cliente.get("/api/v1/salud").json()["base_datos"] == "ok"


def test_viabilidad_ordenada_y_en_rango():
    r = cliente.get("/api/v1/viabilidad", params={"sa6": "611019"})
    assert r.status_code == 200
    scores = [m["score"] for m in r.json()["mercados"] if m["score"] is not None]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)


def test_ficha_de_mercado_completa():
    iso3 = cliente.get("/api/v1/viabilidad", params={"sa6": "611019"}).json()["mercados"][0]["iso3"]
    f = cliente.get(f"/api/v1/viabilidad/611019/{iso3}").json()
    assert len(f["serie_mensual"]) == 60
    assert {e["escenario"] for e in f["escenarios_economicos"]} == {"conservador", "base", "favorable"}


def test_simulacion_rechaza_pesos_que_no_suman_uno():
    pesos = {"demanda": 0.5, "trayectoria": 0.5, "acceso": 0.5, "competencia": 0, "economico": 0}
    assert cliente.post("/api/v1/viabilidad/611019/simular", json=pesos).status_code == 422


def test_simulacion_con_pesos_srs_reproduce_el_ranking():
    srs = {"demanda": 0.35, "trayectoria": 0.25, "acceso": 0.15, "competencia": 0.15, "economico": 0.10}
    sim = cliente.post("/api/v1/viabilidad/611019/simular", json=srs).json()["mercados"]
    base = cliente.get("/api/v1/viabilidad", params={"sa6": "611019"}).json()["mercados"]
    assert [m["iso3"] for m in sim[:10]] == [m["iso3"] for m in base[:10]]


def test_latencia_rnf01():
    t0 = time.perf_counter()
    cliente.get("/api/v1/viabilidad", params={"sa6": "611019"})
    assert time.perf_counter() - t0 < 2.5
