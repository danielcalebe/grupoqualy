"""Motor de alertas — RB-08."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

# evita duplicar alertas abertos do mesmo tipo/ref
def _ja_aberto(db, tipo: str, ref_tabela: str | None, ref_id: int | None) -> bool:
    row = db.query_one(
        """SELECT id FROM alertas
           WHERE resolvido = 0 AND tipo = ?
             AND COALESCE(ref_tabela,'') = COALESCE(?,'')
             AND COALESCE(ref_id, -1) = COALESCE(?, -1)""",
        (tipo, ref_tabela, ref_id if ref_id is not None else None),
    )
    return row is not None


def _criar(db, tipo, severidade, mensagem, ref_tabela=None, ref_id=None) -> bool:
    if _ja_aberto(db, tipo, ref_tabela, ref_id):
        return False
    db.execute(
        """INSERT INTO alertas (tipo, severidade, mensagem, ref_tabela, ref_id)
           VALUES (?,?,?,?,?)""",
        (tipo, severidade, mensagem, ref_tabela, ref_id),
    )
    return True


def verificar_atraso(db) -> int:
    """em_andamento com chegada prevista + 15 min já passou."""
    criados = 0
    rows = db.query(
        """
        SELECT c.id, c.codigo, c.data_hora_prevista_fim, p.nome AS ponto_nome
        FROM coletas c
        JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
        WHERE c.status = 'em_andamento'
          AND c.data_hora_prevista_fim IS NOT NULL
          AND datetime(c.data_hora_prevista_fim, '+15 minutes') < datetime('now')
        """
    )
    for r in rows:
        if _criar(
            db,
            "atraso",
            "aviso",
            f"{r['codigo']} ({r['ponto_nome']}) com previsão encerrada +15 min sem conclusão.",
            "coletas",
            r["id"],
        ):
            criados += 1
    return criados


def verificar_sem_rota(db) -> int:
    """Veículo ativo sem coletas em dia útil (seg–sex, hoje)."""
    hoje = datetime.now()
    if hoje.weekday() >= 5:
        return 0
    criados = 0
    rows = db.query(
        """
        SELECT v.id, v.placa
        FROM veiculos v
        WHERE v.ativo = 1
          AND NOT EXISTS (
            SELECT 1 FROM coletas c
            WHERE c.veiculo_id = v.id
              AND date(c.data_hora_prevista_inicio) = date('now')
              AND c.status <> 'cancelada'
          )
        """
    )
    for r in rows:
        if _criar(
            db,
            "sem_rota",
            "info",
            f"Veículo {r['placa']} sem coletas alocadas hoje.",
            "veiculos",
            r["id"],
        ):
            criados += 1
    return criados


def verificar_capacidade(db) -> int:
    """Soma estimada do dia por veículo > 100% da capacidade."""
    criados = 0
    rows = db.query(
        """
        SELECT c.veiculo_id, v.placa, v.capacidade_kg,
               SUM(COALESCE(c.peso_estimado_kg, 0)) AS soma
        FROM coletas c
        JOIN veiculos v ON v.id = c.veiculo_id
        WHERE date(c.data_hora_prevista_inicio) = date('now')
          AND c.status NOT IN ('cancelada')
          AND v.capacidade_kg IS NOT NULL
        GROUP BY c.veiculo_id
        HAVING soma > v.capacidade_kg
        """
    )
    for r in rows:
        if _criar(
            db,
            "capacidade",
            "critico",
            f"Veículo {r['placa']}: {r['soma']:.0f} kg estimados > capacidade {r['capacidade_kg']:.0f} kg.",
            "veiculos",
            r["veiculo_id"],
        ):
            criados += 1
    return criados


def verificar_fornecedor_inativo(db) -> int:
    """Ponto frequente (≥3 coletas) sem coleta há 30 dias."""
    criados = 0
    rows = db.query(
        """
        SELECT p.id, p.nome,
               MAX(date(c.data_hora_prevista_inicio)) AS ultima
        FROM pontos_coleta p
        JOIN coletas c ON c.ponto_coleta_id = p.id
        GROUP BY p.id
        HAVING COUNT(*) >= 3
           AND ultima < date('now', '-30 days')
        """
    )
    for r in rows:
        if _criar(
            db,
            "fornecedor_inativo",
            "info",
            f"Ponto '{r['nome']}' sem coleta desde {r['ultima']}.",
            "pontos_coleta",
            r["id"],
        ):
            criados += 1
    return criados


def rodar_motor_alertas(db) -> dict[str, Any]:
    total = 0
    total += verificar_atraso(db)
    total += verificar_sem_rota(db)
    total += verificar_capacidade(db)
    total += verificar_fornecedor_inativo(db)
    return {"criados": total}


def listar_alertas(db, incluir_resolvidos: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM alertas"
    if not incluir_resolvidos:
        sql += " WHERE resolvido = 0"
    sql += " ORDER BY CASE severidade WHEN 'critico' THEN 0 WHEN 'aviso' THEN 1 ELSE 2 END, criado_em DESC"
    return db.query(sql)


def resolver_alerta(db, alerta_id: int) -> bool:
    row = db.execute(
        """UPDATE alertas SET resolvido = 1, resolvido_em = datetime('now')
           WHERE id = ? AND resolvido = 0""",
        (alerta_id,),
    )
    return bool(row)
