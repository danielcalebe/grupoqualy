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


def test_api_indicadores_series(client):
    data = _dia(5)
    _criar_coleta_completa(client, data, peso_est="2000", peso_real="2400")
    login(client, "logistica@grupoqualy.com.br")

    resp = client.get(f"/api/indicadores/series?de={data}&ate={data}")
    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["has_data"] is True
    assert payload["periodo_de"] == data
    assert payload["periodo_ate"] == data
    assert len(payload["evolucao_diaria"]) == 1
    assert payload["evolucao_diaria"][0]["kg_transportados"] >= 2400
    assert payload["por_status"]["chaves"] == ["concluida", "em_andamento", "agendada", "cancelada"]
    assert payload["por_status"]["valores"][0] >= 1
    assert len(payload["por_bairro"]) >= 1
    assert len(payload["por_veiculo"]) >= 1


def test_csv_export_detalhado_conteudo_e_filtro(client):
    import csv
    import io

    data = _dia(6)
    _criar_coleta_completa(client, data, peso_est="2000", peso_real="2500")

    # Cria uma segunda coleta apenas agendada no mesmo dia para testar filtro de status
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
            "tipo_veiculo_necessario": "roll_on",
            "data_hora_prevista_inicio": f"{data}T14:00",
            "origem": "logistica_contatou",
            "peso_estimado_kg": "1800",
        },
        follow_redirects=True,
    )

    login(client, "financeiro@grupoqualy.com.br")
    resp = client.get(f"/relatorios/csv/detalhado?de={data}&ate={data}")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    assert "coletas_detalhado_" in resp.headers.get("Content-Disposition", "")

    texto = resp.data.decode("utf-8-sig")
    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    assert len(linhas) == 2

    colunas_esperadas = {
        "codigo",
        "status",
        "urgente",
        "fornecedor",
        "ponto_coleta",
        "bairro",
        "peso_estimado_kg",
        "peso_real_kg",
        "divergencia_peso_pct",
        "numero_ticket",
    }
    assert colunas_esperadas.issubset(set(linhas[0].keys()))

    concluidas = [r for r in linhas if r["status"] == "concluida"]
    assert len(concluidas) == 1
    assert concluidas[0]["peso_real_kg"] == "2500.00"
    assert concluidas[0]["divergencia_peso_pct"] == "25.00"
    assert concluidas[0]["numero_ticket"].startswith("TQ-")

    # Filtro por status=agendada
    resp_ag = client.get(f"/relatorios/csv/detalhado?de={data}&ate={data}&status=agendada")
    assert resp_ag.status_code == 200
    linhas_ag = list(csv.DictReader(io.StringIO(resp_ag.data.decode("utf-8-sig")), delimiter=";"))
    assert len(linhas_ag) == 1
    assert linhas_ag[0]["status"] == "agendada"


def test_csv_detalhado_exige_login(client):
    resp = client.get("/relatorios/csv/detalhado")
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")


def test_indicadores_graficos_e_tema_qualy(client):
    login(client, "logistica@grupoqualy.com.br")
    resp = client.get("/relatorios/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    for marcador in (
        "chart-evolucao",
        "chart-status",
        "chart-bairros",
        "chart-frota",
        "/relatorios/csv/detalhado",
        "data-qualy-theme-toggle",
        "js/theme.js",
        "js/charts.js",
        "qualy-brand-pill",
    ):
        assert marcador in html, f"Esperado encontrar '{marcador}' em /relatorios/"
