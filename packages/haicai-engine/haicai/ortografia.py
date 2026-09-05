"""Gate ortográfico via LanguageTool local (sidecar HTTP).

Política de referência externa:
- Ortografia oficial = AO90 (Acordo Ortográfico de 1990). O corpus de
  geração é pós-reforma, então o gate vale integralmente para haikus
  gerados. Textos de cânones pré-AO90 (jóia, bóia, anti-higiênico)
  NÃO devem passar por este gate sem normalização prévia.

O servidor LanguageTool roda como sidecar Java em localhost e é
consultado por HTTP — mesmo padrão de um judge LLM, sem depender de
nenhum dentro do loop de RL:

    toolchain/jdk-*/bin/java -Xmx1g \\
        -cp toolchain/LanguageTool-6.4/languagetool-server.jar \\
        org.languagetool.server.HTTPServer --port 8081

Por padrão o gate bloqueia só MISSPELLING: regras gramaticais/de estilo
falso-positam em sintaxe poética; erro de grafia é objetivo.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

LT_URL = os.environ.get("HAICAI_LT_URL", "http://localhost:8081/v2/check")

# Categorias que bloqueiam por padrão (issueType da API do LT).
TIPOS_BLOQUEANTES = frozenset({"misspelling"})

# Vocabulário compilado (built by the lab repo's tools/compila_vocabulario.py
# with LanguageTool 6.4 pt-BR, frozen here as package data for O(1) lookup
# outside the training hot path).
VOCABULARIO = Path(__file__).resolve().parent / "data" / "vocabulario.txt"

TOKEN = re.compile(r"[a-záàâãéêíóôõúüç]+", re.IGNORECASE)


@lru_cache(maxsize=1)
def vocabulario() -> frozenset[str]:
    """Palavras que o LanguageTool considerou bem grafadas."""
    if not VOCABULARIO.exists():
        raise FileNotFoundError(
            f"{VOCABULARIO} não existe — rode tools/compila_vocabulario.py "
            "com o sidecar no ar"
        )
    return frozenset(
        linha.strip().lower()
        for linha in VOCABULARIO.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    )


@dataclass(frozen=True)
class Problema:
    regra: str          # id da regra do LT (ex.: MORFOLOGIK_RULE_PT_BR)
    tipo: str           # issueType (misspelling, grammar, style...)
    mensagem: str
    offset: int         # posição no texto original
    tamanho: int        # comprimento do trecho problemático
    trecho: str
    sugestoes: tuple[str, ...]


def verificar(texto: str, linguagem: str = "pt-BR") -> list[Problema]:
    """Devolve TODOS os apontamentos do LanguageTool para o texto."""
    dados = urllib.parse.urlencode(
        {"text": texto, "language": linguagem}
    ).encode()
    requisicao = urllib.request.Request(
        LT_URL,
        data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            conteudo = json.loads(resposta.read())
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"LanguageTool inacessível em {LT_URL} — suba o sidecar "
            "(ver docstring de ortografia.py)"
        ) from e

    problemas = []
    for m in conteudo.get("matches", []):
        regra = m["rule"]
        problemas.append(
            Problema(
                regra=regra["id"],
                tipo=regra.get("issueType", "desconhecido"),
                mensagem=m.get("message", ""),
                offset=m.get("offset", 0),
                tamanho=m.get("length", 0),
                trecho=texto[m["offset"]: m["offset"] + m.get("length", 0)],
                sugestoes=tuple(
                    r["value"] for r in m.get("replacements", [])
                ),
            )
        )
    return problemas


def bloqueantes(texto: str) -> list[Problema]:
    """Só os problemas que violam o gate (por padrão, ortografia)."""
    return [p for p in verificar(texto) if p.tipo in TIPOS_BLOQUEANTES]


def ortografia_ok(texto: str) -> bool:
    """True se o texto não tem erros de grafia (AO90, pt-BR)."""
    return not bloqueantes(texto)


def tokens_desconhecidos(texto: str) -> list[str]:
    """Palavras fora do vocabulário compilado (qualquer caixa).

    Token capitalizado com minúscula desconhecida TAMBÉM audita: maiúscula
    não é salvo-conduto — 'Amazena' não vira nome próprio por começar
    grande. Quem decide é o sidecar ao vivo (aceita 'Brasil', rejeita
    grafia errada).
    """
    return [
        t
        for t in TOKEN.findall(texto)
        if t.lower() not in vocabulario()
    ]


# Cache de fallback: cada palavra única (válida ou quebrada) consulta o
# sidecar UMA vez na vida do processo. Palavra quebrada não paga de novo.
_vereditos: dict[str, bool] = {}


def gate_rapido(texto: str) -> tuple[bool, list[Problema]]:
    """Gate O(1)-amortizado para o loop de treino.

    Consulta o vocabulário compilado; tokens desconhecidos passam pelo
    fallback ao vivo uma única vez (veredito fica em cache, positivo ou
    negativo). Devolve (ok, problemas_bloqueantes).
    """
    desconhecidas = tokens_desconhecidos(texto)
    if not desconhecidas:
        return True, []

    novas = [t for t in desconhecidas if t.lower() not in _vereditos]
    if novas:
        quebradas = {
            p.trecho.lower().strip()
            for p in verificar(" ".join(novas))
            if p.tipo in TIPOS_BLOQUEANTES
        }
        for token in novas:
            _vereditos[token.lower()] = token.lower() not in quebradas

    problemas = [
        Problema(
            regra="CACHE_NEGATIVO",
            tipo="misspelling",
            mensagem="palavra rejeitada pelo LanguageTool (cache)",
            offset=texto.lower().find(token.lower()),
            tamanho=len(token),
            trecho=token,
            sugestoes=(),
        )
        for token in dict.fromkeys(desconhecidas)
        if not _vereditos[token.lower()]
    ]
    return not problemas, problemas
