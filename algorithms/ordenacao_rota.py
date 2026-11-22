"""Ordenação de rota com 2-opt leve (RB-04)."""
from __future__ import annotations

from typing import Any, Optional

from services.integrations.google_maps import get_distancia_tempo


def _custo_rota(
    rota: list[dict[str, Any]],
    patio: tuple[float, float],
) -> float:
    if not rota:
        return 0.0
    total = 0.0
    atual = patio
    for p in rota:
        lat, lng = p.get("latitude"), p.get("longitude")
        destino = (lat, lng) if lat is not None else patio
        km, _ = get_distancia_tempo(atual, destino)
        total += km
        if lat is not None:
            atual = (lat, lng)
    # volta ao pátio
    km, _ = get_distancia_tempo(atual, patio)
    total += km
    return total


def two_opt(
    rota: list[dict[str, Any]],
    patio: tuple[float, float],
    max_iter: int = 20,
) -> list[dict[str, Any]]:
    """Melhora a rota invertendo sub-sequências enquanto houver ganho."""
    melhor = list(rota)
    melhor_custo = _custo_rota(melhor, patio)
    n = len(melhor)
    if n < 3:
        return melhor

    melhorou = True
    it = 0
    while melhorou and it < max_iter:
        melhorou = False
        it += 1
        for i in range(n - 1):
            for j in range(i + 1, n):
                candidata = melhor[:i] + melhor[i : j + 1][::-1] + melhor[j + 1 :]
                c = _custo_rota(candidata, patio)
                if c < melhor_custo - 0.01:
                    melhor = candidata
                    melhor_custo = c
                    melhorou = True
    return melhor


def ordenar_rota(
    pontos: list[dict[str, Any]],
    patio: tuple[float, float],
    *,
    usar_agrupamento: bool = True,
) -> list[dict[str, Any]]:
    """
    Pipeline completo: agrupa por bairro → vizinho mais próximo → 2-opt.
    """
    from algorithms.agrupamento import agrupar_por_bairro, vizinho_mais_proximo

    if not pontos:
        return []
    if not usar_agrupamento:
        ordenados = vizinho_mais_proximo(pontos, patio)
        return two_opt(ordenados, patio)

    grupos = agrupar_por_bairro(pontos, patio)
    ordem: list[dict[str, Any]] = []
    atual = patio
    for _, pts in grupos:
        sub = vizinho_mais_proximo(pts, atual)
        ordem.extend(sub)
        if sub and sub[-1].get("latitude") is not None:
            atual = (sub[-1]["latitude"], sub[-1]["longitude"])
    return two_opt(ordem, patio)
