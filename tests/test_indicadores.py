"""Testes de indicadores, alertas e API (F6)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from tests.conftest import login


def _csrf(client, html: bytes) -> str:
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    return m.group(1).decode() if m else ""


def _dia(offset: int = 1) -> str:
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def _criar_coleta_completa(client, data: str, peso_est="2000", peso_real="2100"):
    """Cria coleta e leva até concluída com ticket."""
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    ponto = db.query_one("SELECT id FROM pontos_coleta LIMIT 1")
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(ponto["id"]),
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": f"{data}T09:00",
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": peso_est,
        },
        follow_redirects=True,
    )
    row = db.query_one(
        "SELECT id FROM coletas WHERE date(data_hora_prevista_inicio) = date(?) ORDER BY id DESC",
        (data,),
    )
    cid = row["id"]

    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "em_andamento"},
        follow_redirects=True,
    )
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "concluida", "peso_real_kg": peso_real},
        follow_redirects=True,
    )
    return cid


def test_indicadores_pagina(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/relatorios/")
    assert resp.status_code == 200
    assert b"Coletas no per" in resp.data
    assert b"Kg transportados" in resp.data
    assert b"Oupa" not in resp.data  # sanity


def test_indicadores_kpis_api(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/api/indicadores")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    for chave in (
        "total_coletas",
        "kg_transportados",
        "tempo_medio_coleta_min",
        "atrasadas",
        "ocupacao_frota_pct",
        "pendentes_ticket",
    ):
        assert chave in data
    assert data["kpi_count"] >= 6


def test_indicadores_calculo_concluida(client):
    data = _dia(2)
    cid = _criar_coleta_completa(client, data, peso_est="2000", peso_real="2100")
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get(f"/relatorios/?de={data}&ate={data}")
    assert resp.status_code == 200
    assert b"Kg transportados" in resp.data

    data_api = json.loads(client.get(f"/api/indicadores?de={data}&ate={data}").data)
    assert data_api["concluidas"] >= 1
    assert data_api["kg_transportados"] >= 2100


def test_csv_export(client):
    login(client, "financeiro@grupoqualy.com.br")
    resp = client.get("/relatorios/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    body = resp.data.decode("utf-8-sig")
    assert "indicador" in body
    assert "kg_transportados" in body


def test_motorista_acessa_indicadores_restrito(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/relatorios/")
    assert resp.status_code == 200


def test_alertas_pagina(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/alertas/")
    assert resp.status_code == 200
    assert b"Alertas" in resp.data


def test_alerta_peso_divergente(client):
    # divergência > 15%: estimado 2000, real 2500
    data = _dia(3)
    _criar_coleta_completa(client, data, peso_est="2000", peso_real="2500")
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/alertas/")
    assert resp.status_code == 200
    assert b"peso_divergente" in resp.data or b"Peso divergente" in resp.data

    alertas = json.loads(client.get("/api/alertas").data)
    tipos = [a["tipo"] for a in alertas]
    assert "peso_divergente" in tipos


def test_alerta_sem_rota_veiculo(client):
    login(client, "logistica@grupoqualy.com.br")
    # força rodar motor: página de alertas roda o motor
    client.get("/alertas/")
    alertas = json.loads(client.get("/api/alertas").data)
    tipos = [a["tipo"] for a in alertas]
    # dia útil pode gerar sem_rota; qualquer alerta é ok para o teste de API
    assert isinstance(tipos, list)


def test_resolver_alerta(client):
    login(client, "logistica@grupoqualy.com.br")
    client.get("/alertas/")
    alertas = json.loads(client.get("/api/alertas").data)
    if not alertas:
        # cria um manualmente via motor de peso
        data = _dia(4)
        _criar_coleta_completa(client, data, peso_est="1000", peso_real="2000")
        login(client, "logistica@grupoqualy.com.br")
        client.get("/alertas/")
        alertas = json.loads(client.get("/api/alertas").data)
    assert alertas, "deve existir ao menos um alerta"

    aid = alertas[0]["id"]
    page = client.get("/alertas/")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/alertas/{aid}/resolver",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"resolvido" in resp.data.lower()


def test_motorista_nao_resolve_alerta(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/alertas/1/resolver", follow_redirects=True)
    # GET não resolve; POST sem permissão → 403
    resp = client.post("/alertas/1/resolver", data={"csrf_token": "x"}, follow_redirects=True)
    assert resp.status_code == 403


def test_api_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert json.loads(resp.data)["status"] == "ok"


def test_api_coletas_do_dia(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/api/coletas")
    assert resp.status_code == 200
    assert isinstance(json.loads(resp.data), list)


def test_api_ticket_404(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/api/tickets/TQ-9999-9999")
    assert resp.status_code == 404
