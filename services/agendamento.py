"""Serviço de agendamento de coletas — RB-01, RB-02."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from algorithms.conflitos import detectar_conflitos, janela_coleta, parse_dt, sugerir_slots
from config import PARTIDA_PADRAO_PATIO
from services.integrations.google_maps import get_distancia_tempo

PATIO = (-19.9167, -43.9345)  # Grupo Qualy (mock)


def calcular_tempos(
    ponto: dict[str, Any], tipo_veiculo: str, veiculo_tempo_exec: Optional[int] = None
) -> tuple[int, int, int, int]:
    """Retorna (ida_min, volta_min, exec_min, total_min)."""
    # deslocamento: preferir campo do ponto; senão mock Maps; senão 20 min
    if ponto.get("tempo_deslocamento_minutos"):
        ida = int(ponto["tempo_deslocamento_minutos"])
    else:
        _, ida = get_distancia_tempo(
            PATIO,
            (ponto.get("latitude"), ponto.get("longitude")),
        )
    volta = ida
    if veiculo_tempo_exec:
        execucao = int(veiculo_tempo_exec)
    else:
        execucao = 30 if tipo_veiculo == "garra" else 22
    total = ida + execucao + volta
    return ida, volta, execucao, total


def gerar_codigo(db) -> str:
    ano = datetime.now().year
    row = db.query_one(
        "SELECT COUNT(*) AS n FROM coletas WHERE codigo LIKE ?", (f"COL-{ano}-%",)
    )
    seq = (row["n"] if row else 0) + 1
    return f"COL-{ano}-{seq:04d}"


def validar_entrada(form: dict[str, str]) -> list[str]:
    erros = []
    if not form.get("ponto_coleta_id"):
        erros.append("Ponto de coleta é obrigatório.")
    if not form.get("tipo_veiculo_necessario"):
        erros.append("Tipo de veículo é obrigatório.")
    if not form.get("data_hora_prevista_inicio"):
        erros.append("Data/hora de início é obrigatória.")
    if not form.get("origem"):
        erros.append("Origem da solicitação é obrigatória.")
    peso = form.get("peso_estimado_kg")
    if peso:
        try:
            if float(peso) < 0:
                erros.append("Peso estimado não pode ser negativo.")
        except ValueError:
            erros.append("Peso estimado inválido.")
    return erros


def criar_coleta(db, form: dict[str, str], usuario_id: int) -> dict[str, Any]:
    """Cria coleta com cálculo de tempos, janelas e checagem de conflito (RB-01/02)."""
    erros = validar_entrada(form)
    if erros:
        return {"ok": False, "erros": erros}

    ponto = db.query_one(
        "SELECT * FROM pontos_coleta WHERE id = ?", (int(form["ponto_coleta_id"]),)
    )
    if not ponto or not ponto.get("ativo", 1):
        return {"ok": False, "erros": ["Ponto de coleta inválido ou inativo."]}

    tipo = form["tipo_veiculo_necessario"]
    veiculo_id = int(form["veiculo_id"]) if form.get("veiculo_id") else None
    motorista_id = int(form["motorista_id"]) if form.get("motorista_id") else None

    tempo_exec_padrao = None
    if veiculo_id:
        veiculo = db.query_one("SELECT * FROM veiculos WHERE id = ? AND ativo = 1", (veiculo_id,))
        if not veiculo:
            return {"ok": False, "erros": ["Veículo inválido."]}
        if veiculo["tipo"] != tipo and tipo != "carreta_terceirizada":
            if veiculo["tipo"] != tipo:
                return {"ok": False, "erros": ["Tipo do veículo não corresponde à demanda."]}
        tempo_exec_padrao = veiculo["tempo_execucao_padrao_minutos"]

    ida, volta, execucao, total = calcular_tempos(ponto, tipo, tempo_exec_padrao)
    inicio = parse_dt(form["data_hora_prevista_inicio"])
    fim = inicio + timedelta(minutes=total)

    nova_janela = (inicio - timedelta(minutes=ida), fim)
    data_str = inicio.strftime("%Y-%m-%d")

    conflitos = detectar_conflitos(
        db,
        data=data_str,
        veiculo_id=veiculo_id,
        motorista_id=motorista_id,
        nova_janela=nova_janela,
    )
    if conflitos:
        sugestoes = sugerir_slots(
            db,
            data=data_str,
            veiculo_id=veiculo_id,
            motorista_id=motorista_id,
            duracao_min=total,
        )
        return {
            "ok": False,
            "erros": ["Conflito de agenda detectado."],
            "conflitos": conflitos,
            "sugestoes": sugestoes,
        }

    # aviso de gatilho (não bloqueia)
    avisos = []
    peso = float(form["peso_estimado_kg"]) if form.get("peso_estimado_kg") else None
    gatilho = ponto.get("peso_gatilho_kg")
    if peso is not None and gatilho and peso < float(gatilho):
        avisos.append(
            f"Peso estimado ({peso:g} kg) abaixo do gatilho habitual do ponto ({gatilho:g} kg)."
        )

    codigo = gerar_codigo(db)
    urgente = 1 if form.get("urgente") else 0
    observacoes = (form.get("observacoes") or "").strip() or None

    coleta_id = db.execute(
        """INSERT INTO coletas
           (codigo, ponto_coleta_id, veiculo_id, motorista_id, criada_por_usuario_id,
            tipo_veiculo_necessario, origem, status, urgente,
            data_hora_prevista_inicio, data_hora_prevista_fim,
            tempo_deslocamento_ida_minutos, tempo_deslocamento_volta_minutos,
            tempo_execucao_minutos, tempo_total_minutos,
            peso_estimado_kg, observacoes)
           VALUES (?,?,?,?,?,? ,?,'agendada',?,?,?,?,?,?,?,?,?)""",
        (
            codigo,
            ponto["id"],
            veiculo_id,
            motorista_id,
            usuario_id,
            tipo,
            form["origem"],
            urgente,
            inicio.strftime("%Y-%m-%d %H:%M:%S"),
            fim.strftime("%Y-%m-%d %H:%M:%S"),
            ida,
            volta,
            execucao,
            total,
            peso,
            observacoes,
        ),
    )
    db.execute(
        """INSERT INTO historico_status_coleta
           (coleta_id, status_anterior, status_novo, usuario_id, observacao)
           VALUES (?, NULL, 'agendada', ?, 'Coleta criada')""",
        (coleta_id, usuario_id),
    )

    # agenda externa (Google Calendar mock/real)
    try:
        from services.integrations.google_calendar import criar_evento

        evento = criar_evento(
            {
                "id": coleta_id,
                "codigo": codigo,
                "data_hora_prevista_inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "data_hora_prevista_fim": fim.strftime("%Y-%m-%d %H:%M:%S"),
                "ponto_nome": ponto.get("nome"),
                "observacoes": observacoes,
            }
        )
        if evento.get("id"):
            db.execute(
                "UPDATE coletas SET id_evento_agenda_externa = ? WHERE id = ?",
                (evento["id"], coleta_id),
            )
    except Exception:
        pass

    return {"ok": True, "coleta_id": coleta_id, "codigo": codigo, "avisos": avisos}


def listar_coletas(
    db, *, data: Optional[str] = None, status: Optional[str] = None, busca: Optional[str] = None
) -> list[dict[str, Any]]:
    sql = """SELECT c.*, p.nome AS ponto_nome, p.bairro, p.latitude, p.longitude,
                    v.placa, m.nome AS motorista_nome
             FROM coletas c
             JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
             LEFT JOIN veiculos v ON v.id = c.veiculo_id
             LEFT JOIN motoristas m ON m.id = c.motorista_id
             WHERE 1=1"""
    params: list[Any] = []
    if data:
        sql += " AND date(c.data_hora_prevista_inicio) = date(?)"
        params.append(data)
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    if busca:
        sql += " AND (c.codigo LIKE ? OR p.nome LIKE ? OR p.bairro LIKE ?)"
        like = f"%{busca}%"
        params.extend([like, like, like])
    sql += " ORDER BY c.data_hora_prevista_inicio"
    return db.query(sql, params)


def detalhar_coleta(db, coleta_id: int) -> Optional[dict[str, Any]]:
    row = db.query_one(
        """SELECT c.*, p.nome AS ponto_nome, p.bairro, p.logradouro, p.numero,
                  p.cidade, p.uf, p.nome_responsavel, p.contato_responsavel,
                  p.latitude, p.longitude, p.fornecedor_id,
                  f.razao_social AS fornecedor_nome,
                  v.placa, m.nome AS motorista_nome, m.telefone AS motorista_telefone,
                  u.nome AS criada_por_nome,
                  t.numero AS ticket_numero, t.peso_liquido_kg, t.data_hora_descarregamento
           FROM coletas c
           JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
           JOIN fornecedores f ON f.id = p.fornecedor_id
           LEFT JOIN veiculos v ON v.id = c.veiculo_id
           LEFT JOIN motoristas m ON m.id = c.motorista_id
           LEFT JOIN usuarios u ON u.id = c.criada_por_usuario_id
           LEFT JOIN tickets_descarregamento t ON t.coleta_id = c.id
           WHERE c.id = ?""",
        (coleta_id,),
    )
    return row
