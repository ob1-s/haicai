"""Portão 5-7-5 do haicai (projeto haicai; o motor geral vive em `escansao`)."""
from __future__ import annotations

from escansao import Resultado


def forma_ok(v1: Resultado, v2: Resultado, v3: Resultado, largura_max: int | None = None) -> dict:
    """Portão binário do haicai 5-7-5 (por intervalo de contagens defensáveis)."""
    alvos = (5, 7, 5)
    dentro = [alvo in range(r.minimo, r.maximo + 1) for alvo, r in zip(alvos, (v1, v2, v3))]
    largura_ok = True if largura_max is None else max(r.largura for r in (v1, v2, v3)) <= largura_max
    return {"forma_ok": all(dentro) and largura_ok, "versos_ok": dentro, "largura_ok": largura_ok}
