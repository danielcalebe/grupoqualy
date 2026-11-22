"""Testes de agendamento e conflitos (F3)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from tests.conftest import login


def _csrf(client, html: bytes) -> str:
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    return m.group(1).decode() if m else ""


def _ponto_id(client) -> int:
    from core.db import get_db

    row = get_db().query_one("SELECT id FROM pontos_coleta LIMIT 1")
    return row["id"]


def _veiculo_id(tipo: str = "garra") -> int:
    from core.db import get_db

    row = get_db().query_one(
        "SELECT id FROM veiculos WHERE tipo = ? AND ativo = 1 LIMIT 1", (tipo,)
    )
    return row["id"]


def _motorista_id() -> int:
    from core.db import get_db

    row = get_db().query_one("SELECT id FROM motoristas WHERE ativo = 1 LIMIT 1")
    return row["id"]


def _hora(offset_dias: int = 1, hora: int = 8, minuto: int = 0) -> str:
    base = datetime.now() + timedelta(days=offset_dias)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M"
    )


def test_listar_coletas_vazio(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/coletas/")
    assert resp.status_code == 200
    assert b"Nenhuma coleta" in resp.data


def test_form_nova_coleta(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/coletas/nova")
    assert resp.status_code == 200
    assert b"Agendar coleta" in resp.data
    assert b"csrf_token" in resp.data


def test_agendar_coleta_sucesso(client):
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    resp = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(_ponto_id(client)),
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": _hora(1, 8),
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": "2500",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"agendada" in resp.data.lower() or b"COL-" in resp.data


def test_agendar_sem_csrf_falha(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.post(
        "/coletas/nova",
        data={
            "ponto_coleta_id": "1",
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": _hora(),
            "origem": "fornecedor_solicitou",
        },
    )
    assert resp.status_code == 400


def test_motorista_nao_agenda(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/coletas/nova")
    assert resp.status_code == 403


def test_conflito_mesmo_veiculo(client):
    """Duas coletas no mesmo veículo com janelas sobrepostas → 2ª bloqueada."""
    from core.db import get_db

    login(client, "logistica@grupoqualy.com.br")
    vid = _veiculo_id("garra")
    pid = _ponto_id(client)
    hora = _hora(2, 8)

    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    r1 = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(pid),
            "tipo_veiculo_necessario": "garra",
            "veiculo_id": str(vid),
            "data_hora_prevista_inicio": hora,
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": "2000",
        },
        follow_redirects=True,
    )
    assert b"agendada" in r1.data.lower() or b"COL-" in r1.data

    # segunda no mesmo veículo, 30 min depois (sobreposição porque ida+exec+volta > 30)
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    hora2 = (datetime.strptime(hora, "%Y-%m-%dT%H:%M") + timedelta(minutes=30)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    r2 = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(pid),
            "tipo_veiculo_necessario": "garra",
            "veiculo_id": str(vid),
            "data_hora_prevista_inicio": hora2,
            "origem": "logistica_contatou",
        },
        follow_redirects=True,
    )
    assert b"Conflito" in r2.data or b"conflito" in r2.data.lower()


def test_sem_conflito_horarios_distintos(client):
    login(client, "logistica@grupoqualy.com.br")
    vid = _veiculo_id("garra")
    pid = _ponto_id(client)

    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(pid),
            "tipo_veiculo_necessario": "garra",
            "veiculo_id": str(vid),
            "data_hora_prevista_inicio": _hora(3, 8),
            "origem": "fornecedor_solicitou",
        },
        follow_redirects=True,
    )

    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    r = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(pid),
            "tipo_veiculo_necessario": "garra",
            "veiculo_id": str(vid),
            "data_hora_prevista_inicio": _hora(3, 14),
            "origem": "fornecedor_solicitou",
        },
        follow_redirects=True,
    )
    assert b"Conflito" not in r.data


def test_bloqueio_disponibilidade_motorista(client):
    from core.db import get_db

    login(client, "logistica@grupoqualy.com.br")
    mid = _motorista_id()
    pid = _ponto_id(client)
    dia = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    db = get_db()
    db.execute(
        """INSERT INTO disponibilidades_motorista
           (motorista_id, inicio, fim, disponivel, motivo)
           VALUES (?, ?, ?, 0, 'Folga')""",
        (mid, f"{dia} 00:00:00", f"{dia} 23:59:59"),
    )

    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    resp = client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(pid),
            "tipo_veiculo_necessario": "garra",
            "motorista_id": str(mid),
            "data_hora_prevista_inicio": f"{dia}T09:00",
            "origem": "fornecedor_solicitou",
        },
        follow_redirects=True,
    )
    assert b"Conflito" in resp.data or b"Folga" in resp.data


def test_api_conflitos_check(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.post(
        "/coletas/api/conflitos-check",
        json={
            "ponto_coleta_id": _ponto_id(client),
            "tipo_veiculo_necessario": "garra",
            "data_hora_prevista_inicio": _hora(4, 9),
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "conflitos" in data
    assert data["tempo_total_minutos"] and data["tempo_total_minutos"] > 0


def test_detalhe_coleta(client):
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/coletas/nova")
    token = _csrf(client, page.data)
    client.post(
        "/coletas/nova",
        data={
            "csrf_token": token,
            "ponto_coleta_id": str(_ponto_id(client)),
            "tipo_veiculo_necessario": "roll_on",
            "data_hora_prevista_inicio": _hora(6, 10),
            "origem": "fornecedor_solicitou",
            "peso_estimado_kg": "1500",
        },
        follow_redirects=True,
    )
    from core.db import get_db

    row = get_db().query_one("SELECT id, codigo FROM coletas ORDER BY id DESC LIMIT 1")
    resp = client.get(f"/coletas/{row['id']}")
    assert resp.status_code == 200
    assert row["codigo"].encode() in resp.data
