"""Serviço de rotas diárias — geração, cálculo e programação (RB-04)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from algorithms.conflitos import parse_dt
from algorithms.ordenacao_rota import ordenar_rota
from config import PARTIDA_PADRAO_PATIO
from services.integrations.google_maps import get_distancia_tempo

PATIO = (-19.9167, -43.9345)


def coletas_do_dia_para_veiculo(
    db, data: str, veiculo_id: Optional[int] = None, motorista_id: Optional[int] = None
) -> list[dict[str, Any]]:
    sql = """SELECT c.*, p.nome AS ponto_nome, p.bairro, p.latitude, p.longitude,
                    p.tempo_deslocamento_minutos AS ponto_tempo_desloc
             FROM coletas c
             JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
             WHERE c.status = 'agendada'
               AND date(c.data_hora_prevista_inicio) = date(?)"""
    params: list[Any] = [data]
    if veiculo_id:
        sql += " AND (c.veiculo_id = ? OR c.veiculo_id IS NULL)"
        params.append(veiculo_id)
    if motorista_id:
        sql += " AND (c.motorista_id = ? OR c.motorista_id IS NULL)"
        params.append(motorista_id)
    sql += " ORDER BY c.data_hora_prevista_inicio"
    return db.query(sql, params)


def gerar_rota(
    db, *, data: str, veiculo_id: int, motorista_id: int, usuario_id: int
) -> dict[str, Any]:
    veiculo = db.query_one("SELECT * FROM veiculos WHERE id = ? AND ativo = 1", (veiculo_id,))
    motorista = db.query_one(
        "SELECT * FROM motoristas WHERE id = ? AND ativo = 1", (motorista_id,)
    )
    if not veiculo:
        return {"ok": False, "erros": ["Veículo inválido."]}
    if not motorista:
        return {"ok": False, "erros": ["Motorista inválido."]}
    if veiculo["tipo"] != "carreta_terceirizada":
        # coletas podem exigir tipo diferente — filtra por compatibilidade
        pass

    coletas = coletas_do_dia_para_veiculo(db, data, veiculo_id, motorista_id)
    if not coletas:
        return {"ok": False, "erros": ["Nenhuma coleta agendada para este veículo/data."]}

    # capacidade (aviso se exceder; bloqueio se >120%)
    if veiculo.get("capacidade_kg"):
        soma = sum(c.get("peso_estimado_kg") or 0 for c in coletas)
        if soma > float(veiculo["capacidade_kg"]) * 1.2:
            return {
                "ok": False,
                "erros": [
                    f"Capacidade estourada: {soma:.0f} kg > 120% de {veiculo['capacidade_kg']:.0f} kg."
                ],
            }

    pontos = []
    for c in coletas:
        pontos.append(
            {
                "coleta_id": c["id"],
                "codigo": c["codigo"],
                "nome": c["ponto_nome"],
                "bairro": c["bairro"],
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude"),
                "peso_estimado_kg": c.get("peso_estimado_kg"),
                "tempo_execucao_minutos": c.get("tempo_execucao_minutos") or 30,
                "tempo_deslocamento_minutos": c.get("ponto_tempo_desloc"),
            }
        )

    ordenados = ordenar_rota(pontos, PATIO)

    # encadeia horários a partir da partida padrão
    partida = parse_dt(data) + timedelta(minutes=PARTIDA_PADRAO_PATIO)
    atual = partida
    distancia_total = 0.0
    tempo_total = 0
    anterior_coords = PATIO
    resultado_ordem = []

    for i, p in enumerate(ordenados, start=1):
        # deslocamento
        if p.get("latitude") is not None:
            km, minutos = get_distancia_tempo(anterior_coords, (p["latitude"], p["longitude"]))
            anterior_coords = (p["latitude"], p["longitude"])
        else:
            km = 0.0
            minutos = p.get("tempo_deslocamento_minutos") or 20
        chegada = atual + timedelta(minutes=minutos)
        execucao = int(p.get("tempo_execucao_minutos") or 30)
        saida = chegada + timedelta(minutes=execucao)
        distancia_total += km
        tempo_total += minutos + execucao

        db.execute(
            "UPDATE coletas SET ordem_na_rota = ?, rota_diaria_id = NULL, "
            "data_hora_prevista_inicio = ?, data_hora_prevista_fim = ?, "
            "tempo_deslocamento_ida_minutos = ?, tempo_execucao_minutos = ?, "
            "tempo_total_minutos = ?, veiculo_id = ?, motorista_id = ?, "
            "atualizado_em = datetime('now') WHERE id = ?",
            (
                i,
                chegada.strftime("%Y-%m-%d %H:%M:%S"),
                saida.strftime("%Y-%m-%d %H:%M:%S"),
                minutos,
                execucao,
                minutos + execucao,
                veiculo_id,
                motorista_id,
                p["coleta_id"],
            ),
        )
        resultado_ordem.append(
            {
                "ordem": i,
                "codigo": p["codigo"],
                "nome": p["nome"],
                "bairro": p["bairro"],
                "chegada": chegada.strftime("%H:%M"),
                "saida": saida.strftime("%H:%M"),
                "km": round(km, 2),
            }
        )
        atual = saida

    # volta ao pátio
    km_volta, min_volta = get_distancia_tempo(anterior_coords, PATIO)
    distancia_total += km_volta
    tempo_total += min_volta

    # grava rota
    rota_id = db.execute(
        """INSERT INTO rotas_diarias
           (data, veiculo_id, motorista_id, elaborada_por_usuario_id,
            distancia_total_prevista_km, tempo_total_previsto_minutos)
           VALUES (?,?,?,?,?,?)""",
        (
            data,
            veiculo_id,
            motorista_id,
            usuario_id,
            int(round(distancia_total)),
            tempo_total,
        ),
    )
    for item in resultado_ordem:
        db.execute(
            "UPDATE coletas SET rota_diaria_id = ? WHERE codigo = ?",
            (rota_id, item["codigo"]),
        )

    # capacidade aviso
    avisos = []
    if veiculo.get("capacidade_kg"):
        soma = sum(c.get("peso_estimado_kg") or 0 for c in coletas)
        if soma > float(veiculo["capacidade_kg"]):
            avisos.append(
                f"Atenção: soma estimada {soma:.0f} kg excede capacidade {veiculo['capacidade_kg']:.0f} kg."
            )

    return {
        "ok": True,
        "rota_id": rota_id,
        "ordem": resultado_ordem,
        "distancia_km": round(distancia_total, 1),
        "tempo_total_minutos": tempo_total,
        "avisos": avisos,
    }


def listar_rotas(db, data: Optional[str] = None) -> list[dict[str, Any]]:
    sql = """SELECT r.*, v.placa, v.tipo AS veiculo_tipo, m.nome AS motorista_nome,
                    u.nome AS elaborada_por_nome,
                    (SELECT COUNT(*) FROM coletas c WHERE c.rota_diaria_id = r.id) AS n_coletas
             FROM rotas_diarias r
             JOIN veiculos v ON v.id = r.veiculo_id
             JOIN motoristas m ON m.id = r.motorista_id
             JOIN usuarios u ON u.id = r.elaborada_por_usuario_id
             WHERE 1=1"""
    params: list[Any] = []
    if data:
        sql += " AND r.data = ?"
        params.append(data)
    sql += " ORDER BY r.data DESC, v.placa"
    return db.query(sql, params)


def detalhar_rota(db, rota_id: int) -> Optional[dict[str, Any]]:
    rota = db.query_one(
        """SELECT r.*, v.placa, v.tipo AS veiculo_tipo, m.nome AS motorista_nome,
                  m.telefone AS motorista_telefone,
                  u.nome AS elaborada_por_nome
           FROM rotas_diarias r
           JOIN veiculos v ON v.id = r.veiculo_id
           JOIN motoristas m ON m.id = r.motorista_id
           JOIN usuarios u ON u.id = r.elaborada_por_usuario_id
           WHERE r.id = ?""",
        (rota_id,),
    )
    if not rota:
        return None
    coletas = db.query(
        """SELECT c.*, p.nome AS ponto_nome, p.bairro, p.logradouro, p.numero,
                  p.nome_responsavel, p.contato_responsavel, p.latitude, p.longitude
           FROM coletas c
           JOIN pontos_coleta p ON p.id = c.ponto_coleta_id
           WHERE c.rota_diaria_id = ?
           ORDER BY c.ordem_na_rota""",
        (rota_id,),
    )
    rota["coletas"] = coletas
    return rota
