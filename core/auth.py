"""Autenticação, sessão e controle de acesso por perfil (RF-002/RF-003)."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from core.db import get_db
from core.models import PERFIS, Usuario

bp_auth = Blueprint("auth", __name__, url_prefix="")


# ======================= HASH =======================

def hash_senha(senha: str) -> str:
    return generate_password_hash(senha)


def conferir_senha(senha_hash: str, senha: str) -> bool:
    return check_password_hash(senha_hash, senha)


# ======================= SESSÃO =======================

def login_usuario(usuario: Usuario) -> None:
    session.clear()
    session["usuario_id"] = usuario.id
    session["perfil"] = usuario.perfil
    session["nome"] = usuario.nome


def logout_usuario() -> None:
    session.clear()


def usuario_atual() -> Optional[Usuario]:
    uid = session.get("usuario_id")
    if not uid:
        return None
    row = get_db().query_one("SELECT * FROM usuarios WHERE id = ? AND ativo = 1", (uid,))
    return Usuario.from_row(row) if row else None


def carregar_usuario_atual() -> None:
    g.usuario = usuario_atual()


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("usuario") is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def requer_permissao(acao: str) -> Callable:
    """Decorator: exige login + ação na matriz RB-09."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = g.get("usuario")
            if user is None:
                return redirect(url_for("auth.login", next=request.path))
            if not user.pode(acao):
                return render_template(
                    "403.html",
                    acao=acao,
                    perfil=user.perfil,
                ), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def requer_perfis(*perfis: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = g.get("usuario")
            if user is None:
                return redirect(url_for("auth.login", next=request.path))
            if user.perfil not in perfis:
                return render_template(
                    "403.html",
                    acao=" / ".join(perfis),
                    perfil=user.perfil,
                ), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


# ======================= ROTAS DE LOGIN =======================

@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if g.get("usuario"):
        return redirect(url_for("painel.home"))

    erro = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        row = get_db().query_one(
            "SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,)
        )
        if row is None or not conferir_senha(row["senha_hash"], senha):
            erro = "E-mail ou senha inválidos."
        else:
            usuario = Usuario.from_row(row)
            login_usuario(usuario)
            destino = request.args.get("next") or url_for("painel.home")
            if not destino.startswith("/"):
                destino = url_for("painel.home")
            return redirect(destino)

    return render_template("auth/login.html", erro=erro)


@bp_auth.route("/logout", methods=["POST", "GET"])
def logout():
    logout_usuario()
    return redirect(url_for("auth.login"))


def registrar_perfis_permitidos() -> list[str]:
    return list(PERFIS)
