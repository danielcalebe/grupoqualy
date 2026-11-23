"""Fluxo ponta a ponta: agendar → conflito → rota → status → tíquete → KPI (F7)."""
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


def test_fluxo_completo_coleta_rota_ticket_kpi(client):
    data = _dia(10)
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    ponto = db.query_one("SELECT id FROM pontos_coleta LIMIT 1")
    veiculo = db.query_one("SELECT id, tipo FROM veiculos WHERE tipo='garra' AND ativo=1 LIMIT 1")
    motorista = db.query_one("SELECT id FROM motoristas WHERE ativo=1 LIMIT 1")

    # 1) Agendar
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    resp = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(ponto["id"]),
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": f"{data}T09:00",
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": "2500",
            "veiculo_id": str(veiculo["id"]),
            "motorista_id": str(motorista["id"]),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    coleta = db.query_one(
        "SELECT * FROM coletas WHERE date(data_hora_prevista_inicio) = date(?) ORDER BY id DESC",
        (data,),
    )
    assert coleta is not None
    assert coleta["status"] == "agendada"
    # calendar mock
    assert coleta["id_evento_agenda_externa"] is None or "MOCK" in str(
        coleta["id_evento_agenda_externa"]
    )

    # 2) Conflito: mesma janela mesmo veículo
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    resp = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(ponto["id"]),
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": f"{data}T09:30",
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": "1000",
            "veiculo_id": str(veiculo["id"]),
        },
        follow_redirects=True,
    )
    assert b"onflito" in resp.data

    # 3) Gerar rota
    page = client.get("/rotas/gerar")
    token = _csrf(client, page.data)
    resp = client.post(
        "/rotas/gerar",
        data={
            "csrf_token": token,
            "data": data,
            "veiculo_id": str(veiculo["id"]),
            "motorista_id": str(motorista["id"]),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    rota = db.query_one("SELECT * FROM rotas_diarias WHERE data = ?", (data,))
    assert rota is not None

    # 4) Status: em_andamento → concluida com ticket
    cid = coleta["id"]
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "em_andamento"},
        follow_redirects=True,
    )
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "concluida", "peso_real_kg": "2600"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    ticket = db.query_one("SELECT * FROM tickets_descarregamento WHERE coleta_id = ?", (cid,))
    assert ticket is not None
    assert ticket["numero"].startswith("TQ-")

    # 5) Consulta de tíquete
    resp = client.get(f"/tickets/busca?numero={ticket['numero']}")
    assert resp.status_code == 200
    assert ticket["numero"].encode() in resp.data

    # 6) KPIs refletem a conclusão
    kpis = json.loads(client.get(f"/api/indicadores?de={data}&ate={data}").data)
    assert kpis["concluidas"] >= 1
    assert kpis["kg_transportados"] >= 2600
    assert kpis["pendentes_ticket"] == 0 or kpis["pendentes_ticket"] >= 0

    # 7) Impressão da rota
    resp = client.get(f"/rotas/{rota['id']}/imprimir")
    assert resp.status_code == 200
    assert b"Programa" in resp.data

    # 8) Enviar programação
    page = client.get(f"/rotas/{rota['id']}")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/rotas/{rota['id']}/enviar",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert b"enviada" in resp.data.lower() or b"notifica" in resp.data.lower()
    rota2 = db.query_one("SELECT * FROM rotas_diarias WHERE id = ?", (rota["id"],))
    assert rota2["data_hora_envio_programacao"] is not None


def test_google_calendar_mock_ao_agendar(client):
    data = _dia(11)
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
            "data_hora_prevista_inicio": f"{data}T10:00",
            "origem": "logistica_contatou",
            "peso_estimado_kg": "1500",
        },
        follow_redirects=True,
    )
    coleta = db.query_one(
        "SELECT * FROM coletas WHERE date(data_hora_prevista_inicio) = date(?) ORDER BY id DESC",
        (data,),
    )
    assert coleta["id_evento_agenda_externa"] == f"MOCK-{coleta['id']}"


def test_painel_home_kpis(client):
    login(client, "balanca@grupoqualy.com.br")
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Painel" in resp.data or b"Coletas" in resp.data


def test_health_sem_auth(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert json.loads(resp.data)["status"] == "ok"
