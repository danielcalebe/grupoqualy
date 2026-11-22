"""Testes de autenticação e perfis (F1)."""
from __future__ import annotations

from tests.conftest import login


def test_login_ok(client):
    resp = login(client, "admin@grupoqualy.com.br")
    assert resp.status_code == 200
    assert b"Painel operacional" in resp.data


def test_login_senha_errada(client):
    resp = client.post(
        "/login",
        data={"email": "admin@grupoqualy.com.br", "senha": "errada"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"E-mail ou senha inv" in resp.data


def test_login_email_inexistente(client):
    resp = client.post(
        "/login",
        data={"email": "nao@existe.com", "senha": "x"},
        follow_redirects=True,
    )
    assert b"E-mail ou senha inv" in resp.data


def test_rota_protegida_redireciona(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/logout", follow_redirects=True)
    assert b"Sistema de Log" in resp.data
    # após logout, home deve redirecionar
    resp2 = client.get("/")
    assert resp2.status_code == 302


def test_seed_usuarios_por_perfil(db):
    rows = db.query("SELECT perfil, email FROM usuarios ORDER BY perfil")
    perfis = {r["perfil"] for r in rows}
    assert perfis == {
        "administradora",
        "chefe_logistica",
        "motorista",
        "balanca",
        "financeiro",
    }


def test_matriz_permissoes(db):
    from core.models import Usuario

    row = db.query_one("SELECT * FROM usuarios WHERE perfil = 'motorista'")
    mot = Usuario.from_row(row)
    assert mot.pode("alterar_status")
    assert not mot.pode("cadastros")
    assert not mot.pode("gerar_rota")

    row = db.query_one("SELECT * FROM usuarios WHERE perfil = 'financeiro'")
    fin = Usuario.from_row(row)
    assert fin.pode("ver_indicadores")
    assert not fin.pode("agendar")

    row = db.query_one("SELECT * FROM usuarios WHERE perfil = 'administradora'")
    adm = Usuario.from_row(row)
    assert adm.pode("gerenciar_usuarios")
    assert adm.pode("cancelar")


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_seed_nao_duplica(app):
    from core.db import get_db

    db = get_db()
    n1 = db.query_one("SELECT COUNT(*) AS n FROM usuarios")["n"]
    from core.seed import executar_seed

    executar_seed(db)
    n2 = db.query_one("SELECT COUNT(*) AS n FROM usuarios")["n"]
    assert n1 == n2 == 5
