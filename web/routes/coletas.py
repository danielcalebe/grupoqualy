"""Rotas de coletas: lista, detalhe, criação com conflitos (F3)."""
from __future__ import annotations

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from algorithms.conflitos import detectar_conflitos, janela_coleta, parse_dt, sugerir_slots
from core.auth import login_required, requer_permissao
from core.csrf import csrf_protect, gerar_token
from core.db import get_db
from services import agendamento

bp_coletas = Blueprint("coletas", __name__, url_prefix="/coletas")


def _cs() -> str:
    return gerar_token()


@bp_coletas.route("/")
@login_required
def index():
    data = request.args.get("data") or None
    status = request.args.get("status") or None
    busca = request.args.get("q") or None
    rows = agendamento.listar_coletas(get_db(), data=data, status=status, busca=busca)
    return render_template(
        "coletas/index.html",
        rows=rows,
        filtros={"data": data or "", "status": status or "", "q": busca or ""},
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_coletas.route("/nova", methods=["GET", "POST"])
@requer_permissao("agendar")
@csrf_protect
def nova():
    db = get_db()
    if request.method == "POST":
        form = request.form.to_dict()
        resultado = agendamento.criar_coleta(db, form, g.usuario.id)
        if resultado["ok"]:
            for a in resultado.get("avisos", []):
                flash(a, "warning")
            flash(f"Coleta {resultado['codigo']} agendada.", "success")
            return redirect(url_for("coletas.detalhe", cid=resultado["coleta_id"]))
        for e in resultado.get("erros", []):
            flash(e, "danger")
        return render_template(
            "coletas/form.html",
            form=form,
            conflitos=resultado.get("conflitos"),
            sugestoes=resultado.get("sugestoes"),
            pontos=db.query(
                """SELECT p.id, p.nome, p.bairro, f.razao_social
                   FROM pontos_coleta p JOIN fornecedores f ON f.id = p.fornecedor_id
                   WHERE p.ativo = 1 ORDER BY p.bairro, p.nome"""
            ),
            veiculos=db.query(
                "SELECT id, placa, tipo FROM veiculos WHERE ativo = 1 ORDER BY placa"
            ),
            motoristas=db.query(
                "SELECT id, nome FROM motoristas WHERE ativo = 1 ORDER BY nome"
            ),
            usuario=g.usuario,
            csrf=_cs(),
        )

    return render_template(
        "coletas/form.html",
        form={},
        conflitos=None,
        sugestoes=None,
        pontos=db.query(
            """SELECT p.id, p.nome, p.bairro, f.razao_social
               FROM pontos_coleta p JOIN fornecedores f ON f.id = p.fornecedor_id
               WHERE p.ativo = 1 ORDER BY p.bairro, p.nome"""
        ),
        veiculos=db.query("SELECT id, placa, tipo FROM veiculos WHERE ativo = 1 ORDER BY placa"),
        motoristas=db.query("SELECT id, nome FROM motoristas WHERE ativo = 1 ORDER BY nome"),
        usuario=g.usuario,
        csrf=_cs(),
    )


@bp_coletas.route("/<int:cid>")
@login_required
def detalhe(cid):
    db = get_db()
    coleta = agendamento.detalhar_coleta(db, cid)
    if not coleta:
        flash("Coleta não encontrada.", "warning")
        return redirect(url_for("coletas.index"))
    historico = db.query(
        """SELECT h.*, u.nome AS usuario_nome FROM historico_status_coleta h
           JOIN usuarios u ON u.id = h.usuario_id
           WHERE h.coleta_id = ? ORDER BY h.data_hora DESC""",
        (cid,),
    )
    return render_template(
        "coletas/detalhe.html",
        c=coleta,
        historico=historico,
        usuario=g.usuario,
        csrf=_cs(),
    )


# ======================= API dry-run de conflitos =======================

@bp_coletas.route("/api/conflitos-check", methods=["POST"])
@requer_permissao("agendar")
def api_conflitos_check():
    data = request.get_json(silent=True) or request.form.to_dict()
    db = get_db()
    try:
        ponto = db.query_one(
            "SELECT * FROM pontos_coleta WHERE id = ?", (int(data.get("ponto_coleta_id", 0)),)
        )
        if not ponto:
            return jsonify({"conflitos": [], "sugestoes": [], "tempo_total_minutos": None})
        tipo = data.get("tipo_veiculo_necessario") or ponto["tipo_veiculo_padrao"]
        veiculo_id = int(data["veiculo_id"]) if data.get("veiculo_id") else None
        exec_padrao = None
        if veiculo_id:
            v = db.query_one("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,))
            exec_padrao = v["tempo_execucao_padrao_minutos"] if v else None
        ida, volta, execucao, total = agendamento.calcular_tempos(ponto, tipo, exec_padrao)
        inicio = parse_dt(data["data_hora_prevista_inicio"])
        fim = inicio + __import__("datetime").timedelta(minutes=total)
        conflitos = detectar_conflitos(
            db,
            data=inicio.strftime("%Y-%m-%d"),
            veiculo_id=veiculo_id,
            motorista_id=int(data["motorista_id"]) if data.get("motorista_id") else None,
            nova_janela=(inicio - __import__("datetime").timedelta(minutes=ida), fim),
        )
        sugestoes = []
        if conflitos:
            sugestoes = sugerir_slots(
                db,
                data=inicio.strftime("%Y-%m-%d"),
                veiculo_id=veiculo_id,
                motorista_id=int(data["motorista_id"]) if data.get("motorista_id") else None,
                duracao_min=total,
            )
        return jsonify(
            {
                "conflitos": [
                    {"motivo": c["motivo"], "tipo": c["tipo"]} for c in conflitos
                ],
                "sugestoes": sugestoes,
                "tempo_total_minutos": total,
                "tempo_ida": ida,
                "tempo_execucao": execucao,
            }
        )
    except Exception as exc:
        return jsonify({"erro": str(exc)}), 400
