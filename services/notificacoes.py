"""Notificações a motoristas — mock/estrutura para email/WhatsApp."""
from __future__ import annotations

from typing import Any, Optional


def notificar_motorista(
    db,
    *,
    motorista_id: int,
    mensagem: str,
    coleta_id: Optional[int] = None,
    canal: str = "sistema",
) -> int:
    """Registra notificação (canal sistema = interno; email/whatsapp = mock)."""
    row = db.query_one("SELECT id, ativo FROM motoristas WHERE id = ?", (motorista_id,))
    if not row or not row["ativo"]:
        return 0
    cur = db.execute(
        """INSERT INTO notificacoes_coleta (coleta_id, motorista_id, usuario_id, canal, mensagem)
           VALUES (?,?,?,?,?)""",
        (coleta_id, motorista_id, None, canal, mensagem),
    )
    # Em produção: integrar SMTP/WhatsApp Cloud API conforme canal.
    return cur or 0


def nao_lidas(db, motorista_id: Optional[int] = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM notificacoes_coleta WHERE lida = 0"
    params: list[Any] = []
    if motorista_id:
        sql += " AND motorista_id = ?"
        params.append(motorista_id)
    sql += " ORDER BY data_hora_envio DESC"
    return db.query(sql, params)


def marcar_lida(db, notificacao_id: int) -> bool:
    return bool(
        db.execute(
            "UPDATE notificacoes_coleta SET lida = 1 WHERE id = ?", (notificacao_id,)
        )
    )
