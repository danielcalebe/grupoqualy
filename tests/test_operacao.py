"""Testes de operação: kanban, status e tíquete (F5)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from tests.conftest import login


def _csrf(client, html: bytes) -> str:
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    return m.group(1).decode() if m else ""


def _dia(offset: int = 1) -> str:
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def _criar_coleta(client, data: str) -> int:
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    ponto = db.query_one("SELECT id FROM pontos_coleta LIMIT 1")
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
            "peso_estimado_kg": "2000",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    row = db.query_one(
        "SELECT id FROM coletas WHERE date(data_hora_prevista_inicio) = date(?) ORDER BY id DESC",
        (data,),
    )
    return row["id"]


def test_painel_operacao(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/operacao/")
    assert resp.status_code == 200
    assert b"Painel de opera" in resp.data
    assert b"Agendadas" in resp.data


def test_status_agendada_para_em_andamento(client):
    data = _dia(2)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "em_andamento"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "em_andamento" in resp.data.decode("utf-8") or b"em_andamento" in resp.data

    from core.db import get_db

    c = get_db().query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "em_andamento"
    hist = get_db().query_one(
        "SELECT * FROM historico_status_coleta WHERE coleta_id = ? ORDER BY id DESC",
        (cid,),
    )
    assert hist is not None
    assert hist["status_novo"] == "em_andamento"


def test_transicao_invalida(client):
    data = _dia(3)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "concluida"},  # agendada → concluida inválido
        follow_redirects=True,
    )
    assert b"inv" in resp.data.lower() or b"Transi" in resp.data
    from core.db import get_db

    c = get_db().query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "agendada"


def test_cancelar_exige_observacao(client):
    data = _dia(4)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "cancelada", "observacao": ""},
        follow_redirects=True,
    )
    from core.db import get_db

    c = get_db().query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "agendada"  # cancelamento sem motivo não passa

    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "cancelada", "observacao": "Cliente adiou."},
        follow_redirects=True,
    )
    c = get_db().query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "cancelada"


def test_concluir_gera_ticket(client):
    data = _dia(5)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    # agendada → em_andamento → concluida
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
        data={"csrf_token": token, "status": "concluida", "peso_real_kg": "1900"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    t = db.query_one("SELECT * FROM tickets_descarregamento WHERE coleta_id = ?", (cid,))
    assert t is not None
    assert t["numero"].startswith("TQ-")
    assert t["peso_liquido_kg"] == 1900


def test_busca_ticket(client):
    data = _dia(6)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
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
        data={"csrf_token": token, "status": "concluida", "peso_real_kg": "2000"},
        follow_redirects=True,
    )
    t = db.query_one("SELECT numero FROM tickets_descarregamento WHERE coleta_id = ?", (cid,))

    resp = client.get(f"/tickets/busca?numero={t['numero']}")
    assert resp.status_code == 200
    assert t["numero"].encode() in resp.data
    assert b"Peso" in resp.data


def test_motorista_altera_propria_coleta(client):
    data = _dia(7)
    cid = _criar_coleta(client, data)
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    motorista = db.query_one("SELECT id FROM motoristas WHERE ativo=1 LIMIT 1")
    db.execute("UPDATE coletas SET motorista_id = ? WHERE id = ?", (motorista["id"], cid))

    login(client, "motorista@grupoqualy.com.br")
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    resp = client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "em_andamento"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    c = db.query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "em_andamento"


def test_motorista_sem_alocacao_nao_altera(client):
    data = _dia(8)
    cid = _criar_coleta(client, data)
    login(client, "motorista@grupoqualy.com.br")
    page = client.get("/operacao/")
    token = _csrf(client, page.data)
    client.post(
        f"/operacao/{cid}/status",
        data={"csrf_token": token, "status": "em_andamento"},
        follow_redirects=True,
    )
    from core.db import get_db

    c = get_db().query_one("SELECT status FROM coletas WHERE id = ?", (cid,))
    assert c["status"] == "agendada"  # sem alocação não altera
