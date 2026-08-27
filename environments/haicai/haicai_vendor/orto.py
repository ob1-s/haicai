"""Gate ortográfico runtime, sem sidecar.

Cobertura de vocabulário = fração de tokens encontrados no léxico
compilado (40k palavras validadas pelo LanguageTool sobre corpus
pós-AO90). Erro de grafia e vazamento de outra língua derrubam a
fração; palavra rara legítima custa pouco. Contínuo em [0, 1] —
gradiente suave para RL, determinístico, zero dependências.
"""
from __future__ import annotations

import re
from functools import lru_cache
from importlib import resources
from pathlib import Path

TOKEN = re.compile(r"[a-záàâãéêíóôõúüç]+", re.IGNORECASE)

_VOCAB = Path(__file__).parent / "data" / "vocabulario.txt"


@lru_cache(maxsize=1)
def vocabulario() -> frozenset[str]:
    return frozenset(
        linha.strip().lower()
        for linha in _VOCAB.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    )


def coverage(texto: str) -> float:
    """Fração de tokens do texto presentes no vocabulário compilado."""
    tokens = TOKEN.findall(texto)
    if not tokens:
        return 0.0
    voc = vocabulario()
    return sum(1 for t in tokens if t.lower() in voc) / len(tokens)
