"""Detecção de conflitos de agendamento e sugestão de slots livres (RB-02)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from config import (
    EXPEDIENTE_FIM,
    EXPEDIENTE_INICIO,
    HORIZONTE_SUGESTAO_DIAS,
    LIMITE_SUGESTOES,
    SLOT_SUGESTAO_MINUTOS,
)

STATUS_ATIVOS = ("agendada", "em_andamento")


def parse_dt(valor: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt)
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {valor}")


def janela_coleta(row: dict[str, Any]) -> tuple[datetime, datetime]:
    """[inicio - ida, fim] — a volta já está embutida no fim previsto."""
    inicio = parse_dt(row["data_hora_prevista_inicio"])
    fim = parse_dt(row["data_hora_prevista_fim"])
    ida = int(row.get("tempo_deslocamento_ida_minutos") or 0)
    return inicio - timedelta(minutes=ida), fim


def sobrepor(a: tuple[datetime, datetime], b: tuple[datetime, datetime]) -> bool:
    """Adjacente (fim == início) NÃO é conflito."""
    return a[0] < b[1] and b[0] < a[1]


def detectar_conflitos(
    db,
    *,
    data: str,
    veiculo_id: Optional[int] = None,
    motorista_id: Optional[int] = None,
    nova_janela: tuple[datetime, datetime],
    excluir_coleta_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Retorna lista de conflitos (coletas e bloqueios de disponibilidade)."""
    conflitos: list[dict[str, Any]] = []

    if veiculo_id:
        rows = db.query(
            f"""SELECT * FROM coletas
                WHERE veiculo_id = ?
                  AND status IN ({",".join("?" * len(STATUS_ATIVOS))})
                  AND date(data_hora_prevista_inicio) = date(?)
                  {"AND id != ?" if excluir_coleta_id else ""}""",
            ((veiculo_id, *STATUS_ATIVOS, data, excluir_coleta_id) if excluir_coleta_id
             else (veiculo_id, *STATUS_ATIVOS, data)),
        )
        for r in rows:
            if sobrepor(janela_coleta(r), nova_janela):
                conflitos.append({"tipo": "coleta", "motivo": "veículo ocupado", "coleta": r})

    if motorista_id:
        rows = db.query(
            f"""SELECT * FROM coletas
                WHERE motorista_id = ?
                  AND status IN ({",".join("?" * len(STATUS_ATIVOS))})
                  AND date(data_hora_prevista_inicio) = date(?)
                  {"AND id != ?" if excluir_coleta_id else ""}""",
            ((motorista_id, *STATUS_ATIVOS, data, excluir_coleta_id) if excluir_coleta_id
             else (motorista_id, *STATUS_ATIVOS, data)),
        )
        for r in rows:
            if sobrepor(janela_coleta(r), nova_janela):
                conflitos.append({"tipo": "coleta", "motivo": "motorista ocupado", "coleta": r})

        bloqueios = db.query(
            """SELECT * FROM disponibilidades_motorista
               WHERE motorista_id = ? AND disponivel = 0
                 AND inicio <= ? AND fim >= ?""",
            (
                motorista_id,
                nova_janela[1].strftime("%Y-%m-%d %H:%M:%S"),
                nova_janela[0].strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        for b in bloqueios:
            conflitos.append({"tipo": "bloqueio", "motivo": b.get("motivo") or "indisponível", "bloqueio": b})

    return conflitos


def sugerir_slots(
    db,
    *,
    data: str,
    veiculo_id: Optional[int],
    motorista_id: Optional[int],
    duracao_min: int,
    janelas_ocupadas: Optional[list[tuple[datetime, datetime]]] = None,
) -> list[str]:
    """Próximos slots livres em horizonte de N dias (06:00–18:00, passos de 30 min)."""
    base = parse_dt(data) if len(data) == 10 else parse_dt(data[:10])
    ocupadas = list(janelas_ocupadas or [])

    # coletas já existentes no período
    for r in db.query(
        """SELECT * FROM coletas
           WHERE status IN ('agendada','em_andamento')
             AND date(data_hora_prevista_inicio) >= date(?)
             AND date(data_hora_prevista_inicio) <= date(?, '+' || ? || ' days')""",
        (base.strftime("%Y-%m-%d"), base.strftime("%Y-%m-%d"), HORIZONTE_SUGESTAO_DIAS),
    ):
        if veiculo_id and r.get("veiculo_id") == veiculo_id:
            ocupadas.append(janela_coleta(r))
        if motorista_id and r.get("motorista_id") == motorista_id:
            ocupadas.append(janela_coleta(r))

    sugestoes: list[str] = []
    for dia in range(HORIZONTE_SUGESTAO_DIAS):
        d = base + timedelta(days=dia)
        minutos = EXPEDIENTE_INICIO
        while minutos + duracao_min <= EXPEDIENTE_FIM and len(sugestoes) < LIMITE_SUGESTOES:
            ini = d.replace(hour=0, minute=0) + timedelta(minutes=minutos)
            fim = ini + timedelta(minutes=duracao_min)
            if all(not sobrepor((ini, fim), o) for o in ocupadas):
                sugestoes.append(ini.strftime("%Y-%m-%dT%H:%M"))
            minutos += SLOT_SUGESTAO_MINUTOS
        if len(sugestoes) >= LIMITE_SUGESTOES:
            break
    return sugestoes
