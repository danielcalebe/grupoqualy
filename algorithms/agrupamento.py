"""Agrupamento de pontos de coleta por bairro/proximidade (RB-04)."""
from __future__ import annotations

from typing import Any, Optional

from services.integrations.google_maps import get_distancia_tempo

PATIO = (-19.9167, -43.9345)


def agrupar_por_bairro(
    pontos: list[dict[str, Any]],
    patio: tuple[float, float] = PATIO,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """
    Agrupa pontos por bairro e ordena os bairros pela distância
    acumulada a partir do pátio (mock Maps).
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for p in pontos:
        bairro = (p.get("bairro") or "Sem bairro").strip()
        buckets.setdefault(bairro, []).append(p)

    # centroide mock do bairro = primeira coordenada do grupo
    def dist_bairro(item: tuple[str, list[dict[str, Any]]]) -> float:
        _, pts = item
        coords = [(p.get("latitude"), p.get("longitude")) for p in pts if p.get("latitude")]
        if not coords:
            return 9999.0
        lat = sum(c[0] for c in coords) / len(coords)
        lng = sum(c[1] for c in coords) / len(coords)
        km, _ = get_distancia_tempo(patio, (lat, lng))
        return km

    return sorted(buckets.items(), key=dist_bairro)


def vizinho_mais_proximo(
    pontos: list[dict[str, Any]],
    inicio: tuple[float, float],
) -> list[dict[str, Any]]:
    """Ordena por vizinho mais próximo a partir de `inicio`."""
    restante = list(pontos)
    atual = inicio
    ordem: list[dict[str, Any]] = []
    while restante:
        melhor_i = 0
        melhor_d = float("inf")
        for i, p in enumerate(restante):
            lat, lng = p.get("latitude"), p.get("longitude")
            if lat is None:
                d = 5000.0  # sem coords: prioridade baixa
            else:
                d, _ = get_distancia_tempo(atual, (lat, lng))
            if d < melhor_d:
                melhor_d = d
                melhor_i = i
        p = restante.pop(melhor_i)
        ordem.append(p)
        if p.get("latitude") is not None:
            atual = (p["latitude"], p["longitude"])
    return ordem
