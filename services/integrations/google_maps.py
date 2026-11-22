"""Distância/tempo entre pontos — Google Maps real (se chave) ou mock determinístico."""
from __future__ import annotations

import math
from typing import Optional

from config import GOOGLE_MAPS_API_KEY

_CACHE: dict[tuple, tuple[float, int]] = {}

# Velocidade média urbana (km/h) para o mock
VELOCIDADE_MDIA_KMH = 35.0
FATOR_ESTRADA = 1.3  # desvio em relação à distância em linha reta


def _euclid_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_distancia_tempo(
    origem: tuple[Optional[float], Optional[float]],
    destino: tuple[Optional[float], Optional[float]],
) -> tuple[float, int]:
    """Retorna (km, minutos). Mock se não houver chave ou coordenadas."""
    key = (origem, destino)
    if key in _CACHE:
        return _CACHE[key]

    if GOOGLE_MAPS_API_KEY and origem[0] and destino[0]:
        try:
            result = _google_directions(origem, destino)
            if result:
                _CACHE[key] = result
                return result
        except Exception:
            pass  # fallback mock

    result = _mock(origem, destino)
    _CACHE[key] = result
    return result


def _mock(
    origem: tuple[Optional[float], Optional[float]],
    destino: tuple[Optional[float], Optional[float]],
) -> tuple[float, int]:
    if not origem[0] or not origem[1] or not destino[0] or not destino[1]:
        # sem coordenadas: 8 km / 20 min padrão
        return (8.0, 20)
    km = _euclid_km(origem[0], origem[1], destino[0], destino[1]) * FATOR_ESTRADA
    minutos = int(round(km / VELOCIDADE_MDIA_KMH * 60))
    return (round(km, 2), max(minutos, 5))


def _google_directions(
    origem: tuple[float, float], destino: tuple[float, float]
) -> Optional[tuple[float, int]]:
    """Chamada real à Distance Matrix (requer GOOGLE_MAPS_API_KEY)."""
    import json
    import urllib.request
    import urllib.parse

    o = f"{origem[0]},{origem[1]}"
    d = f"{destino[0]},{destino[1]}"
    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json?"
        + urllib.parse.urlencode({"origins": o, "destinations": d, "key": GOOGLE_MAPS_API_KEY})
    )
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    rows = data.get("rows") or []
    if rows and rows[0].get("elements"):
        el = rows[0]["elements"][0]
        if el.get("status") == "OK":
            km = el["distance"]["value"] / 1000.0
            min_ = int(el["duration"]["value"] / 60)
            return (round(km, 2), min_)
    return None


def limpar_cache() -> None:
    _CACHE.clear()
