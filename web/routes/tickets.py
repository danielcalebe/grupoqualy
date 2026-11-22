"""Consulta de tíquete de descarregamento (P6)."""
from __future__ import annotations

from flask import Blueprint, g, render_template, request

from core.auth import login_required
from core.db import get_db
from services.execucao import buscar_ticket

bp_tickets = Blueprint("tickets", __name__, url_prefix="/tickets")


@bp_tickets.route("/busca")
@login_required
def busca():
    numero = (request.args.get("numero") or "").strip()
    resultado = None
    if numero:
        resultado = buscar_ticket(get_db(), numero)
    return render_template(
        "tickets/busca.html",
        numero=numero,
        resultado=resultado,
        usuario=g.usuario,
    )
