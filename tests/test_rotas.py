"""Testes de rotas diárias: agrupamento, ordenação e geração (F4)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from tests.conftest import login


def _csrf(client, html: bytes) -> str:
    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    return m.group(1).decode() if m else ""


def _dia(offset: int = 1) -> str:
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def _criar_coletas(client, data: str, n: int = 3, veiculo_id: int | None = None):
    """Cria N coletas em horários distintos (sem conflito)."""
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    ponto = db.query_one("SELECT id FROM pontos_coleta LIMIT 1")
    for i in range(n):
        page = client.get("/coletas/nova")
        token = _csrf(client, page.data)
        hora = f"{data}T{8 + i * 2:02d}:00"
        resp = client.post(
            "/coletas/nova",
            data={
                "csrf_token": token,
                "ponto_coleta_id": str(ponto["id"]),
                "tipo_veiculo_necessario": "garra",
                "data_hora_prevista_inicio": hora,
                "origem": "fornecedor_solicitou",
                "peso_estimado_kg": "2000",
                **({"veiculo_id": str(veiculo_id)} if veiculo_id else {}),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
    login(client, "logistica@grupoqualy.com.br")


def test_agrupamento_por_bairro():
    from algorithms.agrupamento import agrupar_por_bairro

    pontos = [
        {"bairro": "Savassi", "latitude": -19.92, "longitude": -43.94},
        {"bairro": "Centro", "latitude": -19.92, "longitude": -43.93},
        {"bairro": "Savassi", "latitude": -19.93, "longitude": -43.95},
        {"bairro": "Barreiro", "latitude": -19.98, "longitude": -43.99},
    ]
    grupos = agrupar_por_bairro(pontos)
    nomes = [g[0] for g in grupos]
    assert "Savassi" in nomes
    savassi = dict(grupos)["Savassi"]
    assert len(savassi) == 2
    # bairros mais próximos do pátio primeiro (BH centro ~ -19.92,-43.93)
    assert nomes[0] in ("Centro", "Savassi")


def test_vizinho_mais_proximo():
    from algorithms.agrupamento import vizinho_mais_proximo

    pts = [
        {"latitude": -19.95, "longitude": -43.99, "nome": "longe"},
        {"latitude": -19.917, "longitude": -43.935, "nome": "perto"},
    ]
    ordem = vizinho_mais_proximo(pts, (-19.9167, -43.9345))
    assert ordem[0]["nome"] == "perto"


def test_two_opt_nao_piora():
    from algorithms.ordenacao_rota import _custo_rota, two_opt

    patio = (-19.9167, -43.9345)
    rota = [
        {"latitude": -19.98, "longitude": -43.99},
        {"latitude": -19.92, "longitude": -43.94},
        {"latitude": -19.95, "longitude": -43.96},
    ]
    antes = _custo_rota(rota, patio)
    depois = _custo_rota(two_opt(rota, patio), patio)
    assert depois <= antes + 0.01


def test_listar_rotas_vazio(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/rotas/")
    assert resp.status_code == 200
    assert b"Nenhuma rota" in resp.data


def test_gerar_rota_fluxo(client):
    data = _dia(2)
    _criar_coletas(client, data, n=3)
    login(client, "logistica@grupoqualy.com.br")

    from core.db import get_db

    db = get_db()
    veiculo = db.query_one("SELECT id FROM veiculos WHERE tipo='garra' AND ativo=1 LIMIT 1")
    motorista = db.query_one("SELECT id FROM motoristas WHERE ativo=1 LIMIT 1")

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
    assert b"Rota gerada" in resp.data or b"Ordem de visita" in resp.data

    rota = db.query_one("SELECT * FROM rotas_diarias WHERE data = ?", (data,))
    assert rota is not None
    assert rota["distancia_total_prevista_km"] >= 0

    # coletas vinculadas e ordenadas
    coletas = db.query(
        "SELECT ordem_na_rota FROM coletas WHERE rota_diaria_id = ? ORDER BY ordem_na_rota",
        (rota["id"],),
    )
    assert len(coletas) == 3
    assert [c["ordem_na_rota"] for c in coletas] == [1, 2, 3]


def test_gerar_rota_sem_coletas_falha(client):
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    veiculo = db.query_one("SELECT id FROM veiculos LIMIT 1")
    motorista = db.query_one("SELECT id FROM motoristas LIMIT 1")
    page = client.get("/rotas/gerar")
    token = _csrf(client, page.data)
    resp = client.post(
        "/rotas/gerar",
        data={
            "csrf_token": token,
            "data": _dia(9),
            "veiculo_id": str(veiculo["id"]),
            "motorista_id": str(motorista["id"]),
        },
        follow_redirects=True,
    )
    assert b"Nenhuma coleta" in resp.data


def test_motorista_nao_gera_rota(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/rotas/gerar")
    assert resp.status_code == 403


def test_imprimir_rota(client):
    data = _dia(3)
    _criar_coletas(client, data, n=2)
    login(client, "logistica@grupoqualy.com.br")
    from core.db import get_db

    db = get_db()
    veiculo = db.query_one("SELECT id FROM veiculos WHERE tipo='garra' LIMIT 1")
    motorista = db.query_one("SELECT id FROM motoristas LIMIT 1")
    page = client.get("/rotas/gerar")
    token = _csrf(client, page.data)
    client.post(
        "/rotas/gerar",
        data={
            "csrf_token": token,
            "data": data,
            "veiculo_id": str(veiculo["id"]),
            "motorista_id": str(motorista["id"]),
        },
        follow_redirects=True,
    )
    rota = db.query_one("SELECT id FROM rotas_diarias WHERE data = ?", (data,))
    resp = client.get(f"/rotas/{rota['id']}/imprimir")
    assert resp.status_code == 200
    assert b"Programa" in resp.data
