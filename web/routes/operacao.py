"""Painel de operação: kanban por cores, mapa e transições de status (F5)."""
from __future__ import annotations

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from core.auth import login_required, requer_permissao
from core.csrf import csrf_protect, gerar_token
from core.db import get_db
from services import execucao as svc_exec

bp_operacao = Blueprint("operacao", __name__, url_prefix="/operacao")


def _cs() -> str:
    return gerar_token()


@bp_operacao.route("/")
@login_required
def painel():
    db = get_db()
    data = request.args.get("data") or None
    if not data:
        from datetime import datetime

        data = datetime.now().strftime("%Y-%m-%d")

    coletas = db.query(
        """SELECT c.*, p.nome AS ponto_nome, p.bairro, p.latitude, p.longitude,
                  p.nome_responsavel, p.contato_responsavel, p.logradouro, p.numero AS pnumero,
                  v.placa, m.nome AS motorista_nome
           FROM coletas c
           JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
           LEFT JOIN veiculos v ON v.id = c.veiculo_id
           LEFT JOIN motoristas m ON m.id = c.motorista_id
           WHERE date(c.data_hora_prevista_inicio) = date(?)
           ORDER BY c.data_hora_prevista_inicio""",
        (data,),
    )

    # agrupa por status para o kanban
    kanban = {"agendada": [], "em_andamento": [], "concluida": [], "cancelada": []}
    for c in coletas:
        kanban.setdefault(c["status"], []).append(c)

    nao_notificadas = db.query(
        "SELECT * FROM notificacoes_coleta WHERE lida = 0 ORDER BY data_hora_envio DESC LIMIT 10"
    )

    return render_template(
        "operacao/painel.html",
        data=data,
        kanban=kanban,
        coletas=coletas,
        nao_notificadas=nao_notificadas,
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_operacao.route("/<int:cid>/status", methods=["POST"])
@login_required
def alterar_status(cid):
    db = get_db()
    novo = request.form.get("status") or ""
    obs = (request.form.get("observacao") or "").strip()
    peso = request.form.get("peso_real_kg")
    peso_f = float(peso) if peso else None

    # motorista só altera próprias coletas alocadas
    coleta = db.query_one("SELECT * FROM coletas WHERE id = ?", (cid,))
    if not coleta:
        flash("Coleta não encontrada.", "warning")
        return redirect(url_for("operacao.painel"))

    if g.usuario.perfil == "motorista":
        if coleta.get("motorista_id") is None:
            flash("Coleta sem motorista alocado.", "danger")
            return redirect(url_for("operacao.painel"))
        if not g.usuario.pode("alterar_status"):
            flash("Sem permissão.", "danger")
            return redirect(url_for("operacao.painel"))

    if not g.usuario.pode("alterar_status"):
        flash("Seu perfil não pode alterar status.", "danger")
        return redirect(url_for("operacao.painel"))

    resultado = svc_exec.alterar_status(
        db,
        coleta_id=cid,
        novo_status=novo,
        usuario_id=g.usuario.id,
        observacao=obs,
        peso_real_kg=peso_f,
    )
    if resultado["ok"]:
        msg = f"{coleta['codigo']} → {novo}."
        if resultado.get("ticket"):
            msg += f" Tíquete {resultado['ticket']}."
        flash(msg, "success")
    else:
        for e in resultado["erros"]:
            flash(e, "danger")
    return redirect(request.referrer or url_for("operacao.painel"))


@bp_operacao.route("/api/status", methods=["POST"])
@login_required
def api_status():
    if not g.usuario.pode("alterar_status"):
        return jsonify({"erro": "Sem permissão."}), 403
    data = request.get_json(silent=True) or {}
    db = get_db()
    resultado = svc_exec.alterar_status(
        db,
        coleta_id=int(data.get("coleta_id", 0)),
        novo_status=data.get("status", ""),
        usuario_id=g.usuario.id,
        observacao=data.get("observacao"),
        peso_real_kg=float(data["peso_real_kg"]) if data.get("peso_real_kg") else None,
    )
    if resultado["ok"]:
        return jsonify(resultado)
    return jsonify({"erro": "; ".join(resultado["erros"])}), 400


@bp_operacao.route("/notificacoes/lidas", methods=["POST"])
@login_required
def marcar_notificacoes():
    get_db().execute("UPDATE notificacoes_coleta SET lida = 1 WHERE lida = 0")
    flash("Notificações marcadas como lidas.", "success")
    return redirect(url_for("operacao.painel"))
