"""Testes de cadastros (F2)."""
from __future__ import annotations

from tests.conftest import login


def _csrf(client, html: bytes) -> str:
    import re

    m = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    return m.group(1).decode() if m else ""


def test_menu_cadastros_aparece_para_logistica(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/")
    assert b"Cadastros" in resp.data


def test_menu_cadastros_oculto_para_motorista(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/")
    assert b"href=\"/cadastros/\"" not in resp.data


def test_motorista_bloqueado_em_cadastros(client):
    login(client, "motorista@grupoqualy.com.br")
    resp = client.get("/cadastros/")
    assert resp.status_code == 403


def test_listar_fornecedores(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/cadastros/fornecedores")
    assert resp.status_code == 200
    assert b"Metal" in resp.data  # seed


def test_criar_fornecedor(client):
    login(client, "admin@grupoqualy.com.br")
    page = client.get("/cadastros/fornecedores/novo")
    token = _csrf(client, page.data)
    resp = client.post(
        "/cadastros/fornecedores/novo",
        data={"csrf_token": token, "razao_social": "Reciclagem Nova Era", "frequente": "1"},
        follow_redirects=True,
    )
    assert b"cadastrado" in resp.data
    assert b"Nova Era" in client.get("/cadastros/fornecedores").data


def test_criar_fornecedor_sem_csrf_falha(client):
    login(client, "admin@grupoqualy.com.br")
    resp = client.post(
        "/cadastros/fornecedores/novo",
        data={"razao_social": "Hack"},
    )
    assert resp.status_code == 400


def test_criar_veiculo(client):
    login(client, "logistica@grupoqualy.com.br")
    page = client.get("/cadastros/veiculos/novo")
    token = _csrf(client, page.data)
    resp = client.post(
        "/cadastros/veiculos/novo",
        data={
            "csrf_token": token,
            "placa": "abc1d23",
            "tipo": "garra",
            "tempo_execucao_padrao_minutos": "28",
        },
        follow_redirects=True,
    )
    assert b"cadastrado" in resp.data
    assert b"ABC1D23" in client.get("/cadastros/veiculos").data


def test_criar_ponto_com_mock_coords(client):
    login(client, "admin@grupoqualy.com.br")
    # precisa de fornecedor
    page = client.get("/cadastros/fornecedores/novo")
    token = _csrf(client, page.data)
    client.post(
        "/cadastros/fornecedores/novo",
        data={"csrf_token": token, "razao_social": "Forn Teste"},
    )
    fid = client.application.config  # noqa
    from core.db import get_db

    row = get_db().query_one("SELECT id FROM fornecedores WHERE razao_social='Forn Teste'")
    page = client.get("/cadastros/pontos/novo")
    token = _csrf(client, page.data)
    resp = client.post(
        "/cadastros/pontos/novo",
        data={
            "csrf_token": token,
            "fornecedor_id": str(row["id"]),
            "nome": "Galpão Teste",
            "logradouro": "Rua A",
            "bairro": "Savassi",
            "cidade": "Belo Horizonte",
            "uf": "MG",
            "nome_responsavel": "Zé",
            "tipo_veiculo_padrao": "roll_on",
        },
        follow_redirects=True,
    )
    assert b"cadastrado" in resp.data
    ponto = get_db().query_one("SELECT * FROM pontos_coleta WHERE nome='Galpão Teste'")
    assert ponto["latitude"] is not None
    assert ponto["longitude"] is not None


def test_so_admin_gerencia_usuarios(client):
    login(client, "logistica@grupoqualy.com.br")
    assert client.get("/cadastros/usuarios").status_code == 403
    login(client, "admin@grupoqualy.com.br")
    assert client.get("/cadastros/usuarios").status_code == 200
