"""Factory da aplicação Flask — Sistema de Logística Grupo Qualy."""
from __future__ import annotations

from pathlib import Path

from flask import Flask, g

from config import DATABASE_PATH, DEBUG, SECRET_KEY
from core.auth import carregar_usuario_atual
from core.db import Database


def create_app(db_path=None) -> Flask:
    root = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(root / "web" / "templates"),
        static_folder=str(root / "web" / "static"),
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    app.config["DATABASE_PATH"] = str(db_path or DATABASE_PATH)

    # Banco da aplicação (ou customizado p/ testes)
    if db_path is not None:
        from core import db as db_module

        db_module.db = Database(db_path)

    # Inicializa schema + seed
    from core.db import get_db

    get_db().init_db()
    from core.seed import garantir_seed

    garantir_seed()

    @app.before_request
    def _before():
        carregar_usuario_atual()

    # Blueprints
    from core.auth import bp_auth
    from web.routes.painel import bp_painel
    from web.routes.cadastros import bp_cadastros
    from web.routes.coletas import bp_coletas
    from web.routes.rotas import bp_rotas
    from web.routes.operacao import bp_operacao
    from web.routes.tickets import bp_tickets
    from web.routes.relatorios import bp_relatorios, bp_alertas, bp_api

    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_painel)
    app.register_blueprint(bp_cadastros)
    app.register_blueprint(bp_coletas)
    app.register_blueprint(bp_rotas)
    app.register_blueprint(bp_operacao)
    app.register_blueprint(bp_tickets)
    app.register_blueprint(bp_relatorios)
    app.register_blueprint(bp_alertas)
    app.register_blueprint(bp_api)

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template

        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template

        return render_template(
            "403.html", acao="recurso", perfil=(g.usuario.perfil if g.usuario else "-")
        ), 403

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5000, debug=DEBUG)
