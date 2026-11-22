"""Rotas diárias: geração, listagem, detalhe e impressão (F4)."""
from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from core.auth import login_required, requer_permissao
from core.csrf import csrf_protect, gerar_token
from core.db import get_db
from services import rotas as svc_rotas

bp_rotas = Blueprint("rotas", __name__, url_prefix="/rotas")


def _cs() -> str:
    return gerar_token()


@bp_rotas.route("/")
@login_required
def index():
    data = request.args.get("data") or None
    rows = svc_rotas.listar_rotas(get_db(), data=data)
    return render_template(
        "rotas/index.html",
        rows=rows,
        filtros={"data": data or ""},
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_rotas.route("/gerar", methods=["GET", "POST"])
@requer_permissao("gerar_rota")
@csrf_protect
def gerar():
    db = get_db()
    if request.method == "POST":
        data = request.form.get("data") or ""
        veiculo_id = request.form.get("veiculo_id")
        motorista_id = request.form.get("motorista_id")
        if not data or not veiculo_id or not motorista_id:
            flash("Data, veículo e motorista são obrigatórios.", "danger")
        else:
            resultado = svc_rotas.gerar_rota(
                db,
                data=data,
                veiculo_id=int(veiculo_id),
                motorista_id=int(motorista_id),
                usuario_id=g.usuario.id,
            )
            if resultado["ok"]:
                for a in resultado.get("avisos", []):
                    flash(a, "warning")
                flash(
                    f"Rota gerada: {len(resultado['ordem'])} coletas · "
                    f"{resultado['distancia_km']} km · {resultado['tempo_total_minutos']} min.",
                    "success",
                )
                return redirect(url_for("rotas.detalhe", rid=resultado["rota_id"]))
            for e in resultado.get("erros", []):
                flash(e, "danger")

    hoje = request.form.get("data") if request.method == "POST" else None
    return render_template(
        "rotas/gerar.html",
        veiculos=db.query("SELECT id, placa, tipo FROM veiculos WHERE ativo = 1 ORDER BY placa"),
        motoristas=db.query("SELECT id, nome FROM motoristas WHERE ativo = 1 ORDER BY nome"),
        hoje=hoje,
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_rotas.route("/<int:rid>")
@login_required
def detalhe(rid):
    rota = svc_rotas.detalhar_rota(get_db(), rid)
    if not rota:
        flash("Rota não encontrada.", "warning")
        return redirect(url_for("rotas.index"))
    return render_template("rotas/detalhe.html", r=rota, usuario=g.usuario, csrf=_cs())


@bp_rotas.route("/<int:rid>/imprimir")
@login_required
def imprimir(rid):
    rota = svc_rotas.detalhar_rota(get_db(), rid)
    if not rota:
        flash("Rota não encontrada.", "warning")
        return redirect(url_for("rotas.index"))
    return render_template("rotas/imprimir.html", r=rota, usuario=g.usuario)


@bp_rotas.route("/<int:rid>/enviar", methods=["POST"])
@requer_permissao("gerar_rota")
@csrf_protect
def enviar(rid):
    db = get_db()
    rota = db.query_one("SELECT * FROM rotas_diarias WHERE id = ?", (rid,))
    if not rota:
        flash("Rota não encontrada.", "warning")
        return redirect(url_for("rotas.index"))
    db.execute(
        "UPDATE rotas_diarias SET data_hora_envio_programacao = datetime('now') WHERE id = ?",
        (rid,),
    )
    # notificação mock para motorista
    db.execute(
        """INSERT INTO notificacoes_coleta (motorista_id, canal, mensagem)
           VALUES (?, 'sistema', ?)""",
        (
            rota["motorista_id"],
            f"Programação do dia {rota['data']} enviada (rota #{rid}).",
        ),
    )
    flash("Programação enviada ao motorista (notificação interna).", "success")
    return redirect(url_for("rotas.detalhe", rid=rid))
