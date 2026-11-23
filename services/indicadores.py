"""Indicadores (KPIs) do sistema — RB-07."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional


def _padrao_periodo(de: Optional[str], ate: Optional[str]) -> tuple[str, str]:
    hoje = datetime.now().date()
    if not ate:
        ate = hoje.isoformat()
    if not de:
        d = datetime.strptime(ate, "%Y-%m-%d").date()
        de = (d - timedelta(days=29)).isoformat()  # 30 dias
    return de, ate


def calcular_indicadores(db, de: Optional[str] = None, ate: Optional[str] = None) -> dict[str, Any]:
    de, ate = _padrao_periodo(de, ate)

    coletas = db.query_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status <> 'cancelada') AS total_dia_periodo,
            COUNT(*) AS total_geral,
            SUM(CASE WHEN status = 'concluida'
                     THEN COALESCE(peso_real_kg, peso_estimado_kg, 0) ELSE 0 END) AS kg_transportados,
            AVG(CASE WHEN status = 'concluida' THEN tempo_execucao_minutos END) AS tempo_medio_min,
            SUM(CASE WHEN status = 'concluida'
                      AND data_hora_real_chegada IS NOT NULL
                      AND data_hora_prevista_fim IS NOT NULL
                      AND datetime(data_hora_real_chegada) >
                          datetime(data_hora_prevista_fim, '+15 minutes')
                     THEN 1 ELSE 0 END) AS atrasadas,
            SUM(CASE WHEN status = 'agendada' THEN 1 ELSE 0 END) AS pendentes,
            SUM(CASE WHEN status = 'em_andamento' THEN 1 ELSE 0 END) AS em_andamento,
            SUM(CASE WHEN status = 'concluida' THEN 1 ELSE 0 END) AS concluidas,
            SUM(CASE WHEN status = 'cancelada' THEN 1 ELSE 0 END) AS canceladas,
            SUM(CASE WHEN urgente = 1 AND status NOT IN ('concluida','cancelada') THEN 1 ELSE 0 END) AS urgentes
        FROM coletas
        WHERE date(data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
        """,
        (de, ate),
    ) or {}

    frota = db.query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM veiculos WHERE ativo = 1) AS veiculos_ativos,
            (SELECT COUNT(DISTINCT veiculo_id) FROM coletas
              WHERE veiculo_id IS NOT NULL
                AND date(data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
                AND status <> 'cancelada') AS veiculos_usados
        """,
        (de, ate),
    ) or {}

    tickets = db.query_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE c.status = 'concluida') AS concluidas,
            COUNT(t.id) AS com_ticket
        FROM coletas c
        LEFT JOIN tickets_descarregamento t ON t.coleta_id = c.id
        WHERE date(c.data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
        """,
        (de, ate),
    ) or {}

    total_veiculos = frota.get("veiculos_ativos") or 0
    usados = frota.get("veiculos_usados") or 0
    concluidas_tickets = tickets.get("concluidas") or 0
    com_ticket = tickets.get("com_ticket") or 0

    return {
        "periodo_de": de,
        "periodo_ate": ate,
        "total_coletas": coletas.get("total_dia_periodo") or 0,
        "total_geral": coletas.get("total_geral") or 0,
        "kg_transportados": float(coletas.get("kg_transportados") or 0),
        "tempo_medio_coleta_min": round(float(coletas.get("tempo_medio_min") or 0), 1),
        "atrasadas": coletas.get("atrasadas") or 0,
        "pendentes": coletas.get("pendentes") or 0,
        "em_andamento": coletas.get("em_andamento") or 0,
        "concluidas": coletas.get("concluidas") or 0,
        "canceladas": coletas.get("canceladas") or 0,
        "urgentes": coletas.get("urgentes") or 0,
        "ocupacao_frota_pct": round(usados / total_veiculos * 100, 1) if total_veiculos else 0.0,
        "veiculos_ativos": total_veiculos,
        "veiculos_usados": usados,
        "pendentes_ticket": max(concluidas_tickets - com_ticket, 0),
        "kpi_count": 6,
    }


def kpis_do_dia(db) -> dict[str, Any]:
    hoje = datetime.now().strftime("%Y-%m-%d")
    return calcular_indicadores(db, de=hoje, ate=hoje)
