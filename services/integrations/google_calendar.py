"""Google Calendar — mock sem credenciais; estrutura real documentada.

Produção (OAuth2 / Service Account):
  1. Defina GOOGLE_CALENDAR_CREDENTIALS com o path do JSON da service account
     ou o conteúdo do JSON.
  2. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  3. Escopo: https://www.googleapis.com/auth/calendar
  4. calendarId = 'primary' ou ID do calendário do setor logística.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from config import GOOGLE_CALENDAR_CREDENTIALS

log = logging.getLogger(__name__)


def criar_evento(coleta: dict[str, Any]) -> dict[str, Any]:
    """
    Cria evento na agenda do setor para a coleta.

    Sem credenciais → mock: id = MOCK-<coleta_id>, grava log.
    Com credenciais → chama Google Calendar API (estrutura abaixo).
    """
    coleta_id = coleta.get("id")
    if not GOOGLE_CALENDAR_CREDENTIALS:
        evento_id = f"MOCK-{coleta_id}"
        log.info(
            "Google Calendar MOCK — coleta %s id=%s inicio=%s",
            coleta.get("codigo"),
            evento_id,
            coleta.get("data_hora_prevista_inicio"),
        )
        return {
            "ok": True,
            "mock": True,
            "id": evento_id,
            "html_link": None,
            "resumo": f"Coleta {coleta.get('codigo')} — {coleta.get('ponto_nome', '')}",
        }

    # Estrutura real (requer biblioteca instalada):
    # from google.oauth2 import service_account
    # from googleapiclient.discovery import build
    # creds = service_account.Credentials.from_service_account_info(
    #     json.loads(GOOGLE_CALENDAR_CREDENTIALS), scopes=[...])
    # service = build('calendar', 'v3', credentials=creds)
    # evento = {
    #     'summary': f"Coleta {coleta.get('codigo')}",
    #     'description': coleta.get('observacoes') or '',
    #     'start': {'dateTime': coleta['data_hora_prevista_inicio'], 'timeZone': 'America/Sao_Paulo'},
    #     'end': {'dateTime': coleta['data_hora_prevista_fim'], 'timeZone': 'America/Sao_Paulo'},
    # }
    # resp = service.events().insert(calendarId='primary', body=evento).execute()
    # return {"ok": True, "mock": False, "id": resp["id"], "html_link": resp.get("htmlLink")}

    log.warning("GOOGLE_CALENDAR_CREDENTIALS definido mas integração real não ativada nesta build.")
    evento_id = f"MOCK-{coleta_id}"
    return {"ok": True, "mock": True, "id": evento_id, "html_link": None}


def sincronizar_evento(coleta_id: int, id_evento: Optional[str]) -> dict[str, Any]:
    """Placeholder para atualização/cancelamento do evento."""
    if not id_evento:
        return {"ok": False, "erro": "Sem id de evento."}
    log.info("Google Calendar — sync mock coleta=%s evento=%s", coleta_id, id_evento)
    return {"ok": True, "mock": True, "id": id_evento}
