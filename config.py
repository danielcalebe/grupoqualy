"""Configuração da aplicação — Sistema de Logística Grupo Qualy."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "logistica.db"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-qualy-change-in-production")
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
DEBUG = FLASK_ENV == "development"

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_CALENDAR_CREDENTIALS = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")

# Janela útil de expedição (minutos desde meia-noite)
EXPEDIENTE_INICIO = 6 * 60   # 06:00
EXPEDIENTE_FIM = 18 * 60     # 18:00
PARTIDA_PADRAO_PATIO = 7 * 60  # 07:00

SLOT_SUGESTAO_MINUTOS = 30
HORIZONTE_SUGESTAO_DIAS = 3
LIMITE_SUGESTOES = 5

ATRASO_ALERTA_MINUTOS = 15
DIVERGENCIA_PESO_ALERTA_PCT = 15
