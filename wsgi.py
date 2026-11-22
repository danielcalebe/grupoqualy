"""Entrypoint WSGI — usar em produção: `gunicorn wsgi:application`."""
from app import create_app

application = create_app()
