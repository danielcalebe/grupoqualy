"""Painel principal (home) — KPIs mínimos na F1, expandido em F6."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, g, render_template

from core.auth import login_required
from core.db import get_db
from services.indicadores import obter_series_graficos

bp_painel = Blueprint("painel", __name__, url_prefix="")


@bp_painel.route("/")
@login_required
def home():
    db = get_db()
    hoje = db.query_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'agendada' THEN 1 ELSE 0 END) AS agendadas,
            SUM(CASE WHEN status = 'em_andamento' THEN 1 ELSE 0 END) AS em_andamento,
            SUM(CASE WHEN status = 'concluida' THEN 1 ELSE 0 END) AS concluidas,
            SUM(CASE WHEN status = 'cancelada' THEN 1 ELSE 0 END) AS canceladas,
            SUM(CASE WHEN urgente = 1 AND status NOT IN ('concluida','cancelada') THEN 1 ELSE 0 END) AS urgentes
        FROM coletas
        WHERE date(data_hora_prevista_inicio) = date('now')
        """
    )
    alertas = db.query(
        "SELECT * FROM alertas WHERE resolvido = 0 ORDER BY criado_em DESC LIMIT 10"
    )
    ultimas = db.query(
        """
        SELECT c.*, p.nome AS ponto_nome, p.bairro
        FROM coletas c
        JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
        ORDER BY c.data_hora_prevista_inicio DESC
        LIMIT 8
        """
    )
    hoje_dt = datetime.now().date()
    series_7d = obter_series_graficos(
        db,
        de=(hoje_dt - timedelta(days=6)).isoformat(),
        ate=hoje_dt.isoformat(),
    )
    return render_template(
        "painel/home.html",
        kpis=hoje or {},
        alertas=alertas,
        ultimas=ultimas,
        series_7d=series_7d,
        usuario=g.usuario,
    )
