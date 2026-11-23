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


_LABELS_TIPO_VEICULO = {
    "garra": "Caminhão Garra",
    "roll_on": "Roll-on / Roll-off",
    "carreta_terceirizada": "Carreta Terceirizada",
}


def obter_series_graficos(
    db, de: Optional[str] = None, ate: Optional[str] = None
) -> dict[str, Any]:
    """Retorna séries estruturadas para os gráficos interativos de indicadores."""
    de, ate = _padrao_periodo(de, ate)

    # 1) Evolução diária no período
    rows_dia = db.query(
        """
        SELECT
            date(data_hora_prevista_inicio) AS dia,
            COUNT(*) FILTER (WHERE status <> 'cancelada') AS total_coletas,
            SUM(CASE WHEN status = 'concluida' THEN 1 ELSE 0 END) AS concluidas,
            SUM(CASE WHEN status = 'concluida'
                     THEN COALESCE(peso_real_kg, peso_estimado_kg, 0) ELSE 0 END) AS kg_transportados
        FROM coletas
        WHERE date(data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
        GROUP BY date(data_hora_prevista_inicio)
        ORDER BY dia ASC
        """,
        (de, ate),
    )
    mapa_dia = {r["dia"]: r for r in rows_dia if r.get("dia")}

    dt_ini = datetime.strptime(de, "%Y-%m-%d").date()
    dt_fim = datetime.strptime(ate, "%Y-%m-%d").date()
    span = (dt_fim - dt_ini).days

    evolucao_diaria: list[dict[str, Any]] = []
    if 0 <= span <= 45:
        for i in range(span + 1):
            d = (dt_ini + timedelta(days=i)).isoformat()
            r = mapa_dia.get(d)
            evolucao_diaria.append(
                {
                    "data": d,
                    "label": f"{d[8:10]}/{d[5:7]}",
                    "total_coletas": int(r["total_coletas"]) if r else 0,
                    "concluidas": int(r["concluidas"] or 0) if r else 0,
                    "kg_transportados": round(float(r["kg_transportados"] or 0), 1) if r else 0.0,
                }
            )
    else:
        for d in sorted(mapa_dia.keys()):
            r = mapa_dia[d]
            evolucao_diaria.append(
                {
                    "data": d,
                    "label": f"{d[8:10]}/{d[5:7]}",
                    "total_coletas": int(r["total_coletas"] or 0),
                    "concluidas": int(r["concluidas"] or 0),
                    "kg_transportados": round(float(r["kg_transportados"] or 0), 1),
                }
            )

    # 2) Distribuição por status
    rows_status = db.query(
        """
        SELECT status, COUNT(*) AS qtd
        FROM coletas
        WHERE date(data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
        GROUP BY status
        """,
        (de, ate),
    )
    mapa_status = {r["status"]: int(r["qtd"] or 0) for r in rows_status}
    chaves_status = ["concluida", "em_andamento", "agendada", "cancelada"]
    labels_status = ["Concluídas", "Em andamento", "Agendadas", "Canceladas"]
    valores_status = [mapa_status.get(k, 0) for k in chaves_status]

    # 3) Top bairros por peso e coletas
    rows_bairro = db.query(
        """
        SELECT
            COALESCE(NULLIF(TRIM(p.bairro), ''), 'Não informado') AS bairro,
            COUNT(*) AS total_coletas,
            SUM(COALESCE(c.peso_real_kg, c.peso_estimado_kg, 0)) AS kg_total
        FROM coletas c
        JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
        WHERE date(c.data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
          AND c.status <> 'cancelada'
        GROUP BY bairro
        ORDER BY kg_total DESC, total_coletas DESC
        LIMIT 8
        """,
        (de, ate),
    )
    por_bairro = [
        {
            "bairro": r["bairro"],
            "total_coletas": int(r["total_coletas"] or 0),
            "kg_total": round(float(r["kg_total"] or 0), 1),
        }
        for r in rows_bairro
    ]

    # 4) Desempenho por veículo
    rows_veic = db.query(
        """
        SELECT
            v.placa,
            v.tipo,
            COALESCE(v.capacidade_kg, 0) AS capacidade_kg,
            COUNT(c.id) AS total_coletas,
            SUM(COALESCE(c.peso_real_kg, c.peso_estimado_kg, 0)) AS kg_total
        FROM veiculos v
        LEFT JOIN coletas c
               ON c.veiculo_id = v.id
              AND date(c.data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
              AND c.status <> 'cancelada'
        WHERE v.ativo = 1
        GROUP BY v.id
        ORDER BY kg_total DESC, total_coletas DESC, v.placa ASC
        """,
        (de, ate),
    )
    por_veiculo = [
        {
            "placa": r["placa"],
            "tipo": r["tipo"],
            "tipo_label": _LABELS_TIPO_VEICULO.get(r["tipo"], r["tipo"]),
            "capacidade_kg": float(r["capacidade_kg"] or 0),
            "total_coletas": int(r["total_coletas"] or 0),
            "kg_total": round(float(r["kg_total"] or 0), 1),
        }
        for r in rows_veic
    ]

    # 5) Por tipo de veículo solicitado
    rows_tipo = db.query(
        """
        SELECT
            tipo_veiculo_necessario AS tipo,
            COUNT(*) AS total_coletas,
            SUM(COALESCE(peso_real_kg, peso_estimado_kg, 0)) AS kg_total
        FROM coletas
        WHERE date(data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
          AND status <> 'cancelada'
        GROUP BY tipo_veiculo_necessario
        ORDER BY total_coletas DESC
        """,
        (de, ate),
    )
    por_tipo_veiculo = [
        {
            "tipo": r["tipo"],
            "label": _LABELS_TIPO_VEICULO.get(r["tipo"], r["tipo"]),
            "total_coletas": int(r["total_coletas"] or 0),
            "kg_total": round(float(r["kg_total"] or 0), 1),
        }
        for r in rows_tipo
    ]

    total_registros = sum(valores_status)
    return {
        "periodo_de": de,
        "periodo_ate": ate,
        "has_data": total_registros > 0,
        "evolucao_diaria": evolucao_diaria,
        "por_status": {
            "chaves": chaves_status,
            "labels": labels_status,
            "valores": valores_status,
        },
        "por_bairro": por_bairro,
        "por_veiculo": por_veiculo,
        "por_tipo_veiculo": por_tipo_veiculo,
    }


def listar_coletas_detalhadas(
    db,
    de: Optional[str] = None,
    ate: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[str, str, list[dict[str, Any]]]:
    """Lista detalhada de coletas + pesagens + tíquetes para prévia e exportação CSV."""
    de, ate = _padrao_periodo(de, ate)

    sql = """
        SELECT
            c.id,
            c.codigo,
            c.status,
            c.urgente,
            c.origem,
            c.tipo_veiculo_necessario,
            c.data_hora_prevista_inicio,
            c.data_hora_prevista_fim,
            c.data_hora_real_saida,
            c.data_hora_real_chegada,
            c.tempo_execucao_minutos,
            c.peso_estimado_kg,
            c.peso_real_kg,
            c.rota_diaria_id,
            c.ordem_na_rota,
            c.observacoes,
            c.motivo_cancelamento,
            p.nome AS ponto_coleta,
            p.bairro,
            p.cidade,
            p.uf,
            f.razao_social AS fornecedor,
            f.cnpj_cpf AS fornecedor_cnpj,
            v.placa AS veiculo_placa,
            v.tipo AS veiculo_tipo,
            m.nome AS motorista,
            t.numero AS numero_ticket,
            t.peso_liquido_kg AS peso_liquido_ticket_kg,
            t.data_hora_descarregamento
        FROM coletas c
        JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
        JOIN fornecedores f ON f.id = p.fornecedor_id
        LEFT JOIN veiculos v ON v.id = c.veiculo_id
        LEFT JOIN motoristas m ON m.id = c.motorista_id
        LEFT JOIN tickets_descarregamento t ON t.coleta_id = c.id
        WHERE date(c.data_hora_prevista_inicio) BETWEEN date(?) AND date(?)
    """
    params: list[Any] = [de, ate]
    if status and status in ("agendada", "em_andamento", "concluida", "cancelada"):
        sql += " AND c.status = ?"
        params.append(status)
    sql += " ORDER BY c.data_hora_prevista_inicio DESC, c.id DESC"

    rows = db.query(sql, params)
    itens: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        est = item.get("peso_estimado_kg")
        real = item.get("peso_real_kg")
        if est is not None and real is not None and float(est) > 0:
            item["divergencia_peso_pct"] = round((float(real) - float(est)) / float(est) * 100.0, 2)
        else:
            item["divergencia_peso_pct"] = None
        itens.append(item)
    return de, ate, itens
