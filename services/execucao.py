"""Transições de status da coleta e tíquete de descarregamento (RB-05, RB-06)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from core.models import TRANSICOES_STATUS

STATUS_LABELS = {
    "agendada": "Agendada",
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
    "cancelada": "Cancelada",
}


def alterar_status(
    db,
    *,
    coleta_id: int,
    novo_status: str,
    usuario_id: int,
    observacao: Optional[str] = None,
    peso_real_kg: Optional[float] = None,
) -> dict[str, Any]:
    coleta = db.query_one("SELECT * FROM coletas WHERE id = ?", (coleta_id,))
    if not coleta:
        return {"ok": False, "erros": ["Coleta não encontrada."]}

    atual = coleta["status"]
    if novo_status == atual:
        return {"ok": False, "erros": ["Coleta já está neste status."]}

    permitidos = TRANSICOES_STATUS.get(atual, ())
    if novo_status not in permitidos:
        return {
            "ok": False,
            "erros": [f"Transição inválida: {atual} → {novo_status}."],
        }

    if novo_status == "cancelada" and not (observacao or "").strip():
        return {"ok": False, "erros": ["Cancelamento exige motivo/observação."]}

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    campos = ["status = ?", "atualizado_em = datetime('now')"]
    params: list[Any] = [novo_status]

    if novo_status == "em_andamento" and not coleta.get("data_hora_real_saida"):
        campos.append("data_hora_real_saida = ?")
        params.append(agora)

    if novo_status == "concluida":
        campos.append("data_hora_real_chegada = ?")
        params.append(agora)
        if peso_real_kg is not None:
            campos.append("peso_real_kg = ?")
            params.append(peso_real_kg)

    if novo_status == "cancelada":
        campos.append("motivo_cancelamento = ?")
        params.append((observacao or "").strip())

    if observacao and novo_status != "cancelada":
        campos.append("observacoes = COALESCE(observacoes, '') || ?")
        params.append(f"\n[{agora}] {observacao}")

    params.append(coleta_id)
    db.execute(f"UPDATE coletas SET {', '.join(campos)} WHERE id = ?", params)

    db.execute(
        """INSERT INTO historico_status_coleta
           (coleta_id, status_anterior, status_novo, usuario_id, observacao)
           VALUES (?,?,?,?,?)""",
        (coleta_id, atual, novo_status, usuario_id, (observacao or "").strip() or None),
    )

    # gera tíquete automaticamente ao concluir (RB-05)
    ticket = None
    if novo_status == "concluida":
        ticket = gerar_ticket(db, coleta_id, peso_real_kg)

    # alerta de divergência de peso
    if (
        novo_status == "concluida"
        and peso_real_kg is not None
        and coleta.get("peso_estimado_kg")
    ):
        est = float(coleta["peso_estimado_kg"])
        if est > 0:
            div = abs(float(peso_real_kg) - est) / est * 100
            if div > 15:
                db.execute(
                    """INSERT INTO alertas (tipo, severidade, mensagem, ref_tabela, ref_id)
                       VALUES ('peso_divergente', 'critico', ?, 'coletas', ?)""",
                    (
                        f"Peso divergente na {coleta['codigo']}: estimado {est:g} kg vs real {peso_real_kg:g} kg ({div:.0f}%).",
                        coleta_id,
                    ),
                )

    # notificação ao motorista em mudanças relevantes
    if coleta.get("motorista_id") and novo_status in ("em_andamento", "concluida", "cancelada"):
        db.execute(
            """INSERT INTO notificacoes_coleta (coleta_id, motorista_id, canal, mensagem)
               VALUES (?,?, 'sistema', ?)""",
            (
                coleta_id,
                coleta["motorista_id"],
                f"{coleta['codigo']}: status → {STATUS_LABELS.get(novo_status, novo_status)}.",
            ),
        )

    return {"ok": True, "ticket": ticket}


def gerar_ticket(
    db, coleta_id: int, peso_liquido_kg: Optional[float] = None
) -> Optional[str]:
    existente = db.query_one(
        "SELECT numero FROM tickets_descarregamento WHERE coleta_id = ?", (coleta_id,)
    )
    if existente:
        return existente["numero"]

    ano = datetime.now().year
    row = db.query_one(
        "SELECT COUNT(*) AS n FROM tickets_descarregamento WHERE numero LIKE ?",
        (f"TQ-{ano}-%",),
    )
    seq = (row["n"] if row else 0) + 1
    numero = f"TQ-{ano}-{seq:04d}"
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        """INSERT INTO tickets_descarregamento
           (coleta_id, numero, peso_liquido_kg, data_hora_descarregamento, pesagem_id)
           VALUES (?,?,?,?,?)""",
        (coleta_id, numero, peso_liquido_kg, agora, None),
    )
    return numero


def buscar_ticket(db, numero: str) -> Optional[dict[str, Any]]:
    return db.query_one(
        """SELECT t.*, c.codigo, c.status, c.peso_estimado_kg, c.peso_real_kg,
                  c.data_hora_prevista_inicio, c.data_hora_real_chegada,
                  p.nome AS ponto_nome, p.bairro, p.logradouro, p.numero AS ponto_numero,
                  p.cidade, p.uf, p.nome_responsavel, p.contato_responsavel,
                  f.razao_social AS fornecedor_nome,
                  v.placa, m.nome AS motorista_nome
           FROM tickets_descarregamento t
           JOIN coletas c ON c.id = t.coleta_id
           JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
           JOIN fornecedores f ON f.id = p.fornecedor_id
           LEFT JOIN veiculos v ON v.id = c.veiculo_id
           LEFT JOIN motoristas m ON m.id = c.motorista_id
           WHERE t.numero = ? OR t.numero = ?""",
        (numero, numero.upper()),
    )
