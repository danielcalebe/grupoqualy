"""Token CSRF simples (sessão) para formulários POST."""
from __future__ import annotations

import secrets
from functools import wraps
from typing import Callable

from flask import abort, request, session


def gerar_token() -> str:
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    return token


def token_atual() -> str | None:
    return session.get("csrf_token")


def validar_form() -> bool:
    esperado = session.get("csrf_token")
    recebido = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not esperado or not recebido or not secrets.compare_digest(esperado, recebido):
        return False
    return True


def csrf_protect(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == "POST" and not validar_form():
            abort(400, description="Token CSRF inválido ou ausente.")
        return view(*args, **kwargs)

    return wrapped
