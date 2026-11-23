"""Relatórios/indicadores (KPIs + CSV) e alertas (F6)."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from flask import Blueprint, Response, flash, g, jsonify, redirect, render_template, request, url_for

from core.auth import login_required, requer_permissao
from core.csrf import csrf_protect, gerar_token
from core.db import get_db
from services import alertas as svc_alertas
from services import indicadores as svc_ind

bp_relatorios = Blueprint("relatorios", __name__, url_prefix="/relatorios")
bp_alertas = Blueprint("alertas", __name__, url_prefix="/alertas")
bp_api = Blueprint("api", __name__, url_prefix="/api")


def _cs() -> str:
    return gerar_token()


# ---------------- Relatórios / indicadores ----------------

def _pode_ver_indicadores() -> bool:
    return g.usuario.pode("ver_indicadores") or g.usuario.pode("ver_indicadores_restrito")


@bp_relatorios.route("/")
@login_required
def index():
    if not _pode_ver_indicadores():
        flash("Sem permissão para ver indicadores.", "danger")
        return redirect(url_for("painel.home"))
    de = request.args.get("de") or ""
    ate = request.args.get("ate") or ""
    status_filtro = (request.args.get("status") or "").strip()
    db = get_db()
    svc_alertas.rodar_motor_alertas(db)
    kpis = svc_ind.calcular_indicadores(db, de or None, ate or None)
    series = svc_ind.obter_series_graficos(db, kpis["periodo_de"], kpis["periodo_ate"])
    _, _, detalhadas = svc_ind.listar_coletas_detalhadas(
        db, kpis["periodo_de"], kpis["periodo_ate"], status=status_filtro or None
    )
    return render_template(
        "relatorios/index.html",
        kpis=kpis,
        series=series,
        coletas_detalhadas=detalhadas,
        filtros={
            "de": kpis["periodo_de"],
            "ate": kpis["periodo_ate"],
            "status": status_filtro,
        },
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_relatorios.route("/csv")
@login_required
def csv_export():
    if not _pode_ver_indicadores():
        flash("Sem permissão.", "danger")
        return redirect(url_for("painel.home"))
    de = request.args.get("de") or None
    ate = request.args.get("ate") or None
    kpis = svc_ind.calcular_indicadores(get_db(), de, ate)

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["indicador", "valor", "periodo_de", "periodo_ate"])
    for chave in (
        "total_coletas",
        "kg_transportados",
        "tempo_medio_coleta_min",
        "atrasadas",
        "ocupacao_frota_pct",
        "pendentes_ticket",
        "concluidas",
        "canceladas",
        "urgentes",
    ):
        w.writerow([chave, kpis[chave], kpis["periodo_de"], kpis["periodo_ate"]])

    dados = buf.getvalue().encode("utf-8-sig")
    nome = f"indicadores_{kpis['periodo_de']}_{kpis['periodo_ate']}.csv"
    return Response(
        dados,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


@bp_relatorios.route("/csv/detalhado")
@login_required
def csv_export_detalhado():
    if not _pode_ver_indicadores():
        flash("Sem permissão.", "danger")
        return redirect(url_for("painel.home"))
    de = request.args.get("de") or None
    ate = request.args.get("ate") or None
    status_filtro = (request.args.get("status") or "").strip() or None
    de_res, ate_res, rows = svc_ind.listar_coletas_detalhadas(
        get_db(), de, ate, status=status_filtro
    )

    colunas = [
        "codigo",
        "status",
        "urgente",
        "data_prevista_inicio",
        "data_prevista_fim",
        "data_real_saida",
        "data_real_chegada",
        "tempo_execucao_min",
        "fornecedor",
        "fornecedor_cnpj",
        "ponto_coleta",
        "bairro",
        "cidade",
        "uf",
        "veiculo_placa",
        "veiculo_tipo",
        "tipo_veiculo_necessario",
        "motorista",
        "peso_estimado_kg",
        "peso_real_kg",
        "divergencia_peso_pct",
        "numero_ticket",
        "peso_liquido_ticket_kg",
        "data_hora_descarregamento",
        "rota_diaria_id",
        "ordem_na_rota",
        "origem",
        "observacoes",
        "motivo_cancelamento",
    ]

    def _fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(colunas)
    for r in rows:
        w.writerow(
            [
                _fmt(r.get("codigo")),
                _fmt(r.get("status")),
                "Sim" if r.get("urgente") else "Não",
                _fmt(r.get("data_hora_prevista_inicio")),
                _fmt(r.get("data_hora_prevista_fim")),
                _fmt(r.get("data_hora_real_saida")),
                _fmt(r.get("data_hora_real_chegada")),
                _fmt(r.get("tempo_execucao_minutos")),
                _fmt(r.get("fornecedor")),
                _fmt(r.get("fornecedor_cnpj")),
                _fmt(r.get("ponto_coleta")),
                _fmt(r.get("bairro")),
                _fmt(r.get("cidade")),
                _fmt(r.get("uf")),
                _fmt(r.get("veiculo_placa")),
                _fmt(r.get("veiculo_tipo")),
                _fmt(r.get("tipo_veiculo_necessario")),
                _fmt(r.get("motorista")),
                _fmt(r.get("peso_estimado_kg")),
                _fmt(r.get("peso_real_kg")),
                _fmt(r.get("divergencia_peso_pct")),
                _fmt(r.get("numero_ticket")),
                _fmt(r.get("peso_liquido_ticket_kg")),
                _fmt(r.get("data_hora_descarregamento")),
                _fmt(r.get("rota_diaria_id")),
                _fmt(r.get("ordem_na_rota")),
                _fmt(r.get("origem")),
                _fmt(r.get("observacoes")),
                _fmt(r.get("motivo_cancelamento")),
            ]
        )

    dados = buf.getvalue().encode("utf-8-sig")
    sufixo = f"_{status_filtro}" if status_filtro else ""
    nome = f"coletas_detalhado_{de_res}_{ate_res}{sufixo}.csv"
    return Response(
        dados,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


# ---------------- Alertas ----------------

@bp_alertas.route("/")
@login_required
def index():
    if not (
        g.usuario.pode("resolver_alertas") or g.usuario.perfil in ("administradora", "chefe_logistica", "balanca")
    ):
        # todos podem ver no painel; página dedicada exige permissão
        if not g.usuario.pode("ver_indicadores"):
            flash("Sem permissão para ver alertas.", "danger")
            return redirect(url_for("painel.home"))

    db = get_db()
    svc_alertas.rodar_motor_alertas(db)
    incluir = request.args.get("todos") == "1"
    rows = svc_alertas.listar_alertas(db, incluir_resolvidos=incluir)
    return render_template(
        "alertas/index.html",
        alertas=rows,
        incluir=incluir,
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_alertas.route("/<int:aid>/resolver", methods=["POST"])
@requer_permissao("resolver_alertas")
@csrf_protect
def resolver(aid):
    ok = svc_alertas.resolver_alerta(get_db(), aid)
    flash("Alerta resolvido." if ok else "Alerta já estava resolvido.", "success" if ok else "warning")
    return redirect(request.referrer or url_for("alertas.index"))


# ---------------- API JSON ----------------

@bp_api.route("/health")
def health():
    return jsonify({"status": "ok", "hora": datetime.now().isoformat(timespec="seconds")})


@bp_api.route("/indicadores")
@login_required
def api_indicadores():
    if not _pode_ver_indicadores():
        return jsonify({"erro": "Sem permissão."}), 403
    de = request.args.get("de")
    ate = request.args.get("ate")
    return jsonify(svc_ind.calcular_indicadores(get_db(), de, ate))


@bp_api.route("/indicadores/series")
@login_required
def api_indicadores_series():
    if not _pode_ver_indicadores():
        return jsonify({"erro": "Sem permissão."}), 403
    de = request.args.get("de")
    ate = request.args.get("ate")
    return jsonify(svc_ind.obter_series_graficos(get_db(), de, ate))


@bp_api.route("/alertas")
@login_required
def api_alertas():
    db = get_db()
    svc_alertas.rodar_motor_alertas(db)
    rows = svc_alertas.listar_alertas(db, incluir_resolvidos=request.args.get("todos") == "1")
    return jsonify(rows)


@bp_api.route("/coletas")
@login_required
def api_coletas():
    data = request.args.get("data") or datetime.now().strftime("%Y-%m-%d")
    rows = get_db().query(
        """SELECT c.id, c.codigo, c.status, c.urgente, c.data_hora_prevista_inicio,
                  c.data_hora_prevista_fim, p.nome AS ponto_nome, p.bairro,
                  p.latitude, p.longitude
           FROM coletas c
           JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
           WHERE date(c.data_hora_prevista_inicio) = date(?)
           ORDER BY c.data_hora_prevista_inicio""",
        (data,),
    )
    return jsonify(rows)


@bp_api.route("/tickets/<numero>")
@login_required
def api_ticket(numero):
    from services.execucao import buscar_ticket

    row = buscar_ticket(get_db(), numero)
    if not row:
        return jsonify({"erro": "Tíquete não encontrado."}), 404
    return jsonify(dict(row))
