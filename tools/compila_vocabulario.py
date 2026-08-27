"""Compila o veredito ortográfico do LanguageTool num conjunto de consulta.

O sidecar Java é LENTO (~200ms/check, teto ~8/s na caixa) e não pode
viver no caminho quente do RL. Mas o veredito dele sobre PALAVRAS é
estável: compilamos uma única vez o vocabulário do corpus (UFSC +
cânones) consultando o LT em lotes, e o gate de treino vira lookup:

    python tools/compila_vocabulario.py

Saída: data/vocabulario_ortografico.txt (uma palavra válida por linha).
Palavras novas descobertas em produção vão para o fallback ao vivo e
podem ser reincorporadas re-executando este script.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CORPUS = Path("/tmp/opencode/surya/poemas")
SAIDA = RAIZ / "data" / "vocabulario_ortografico.txt"
LT = "http://localhost:8081/v2/check"
TAMANHO_LOTE = 500

sys.path.insert(0, str(RAIZ / "tools"))
from valida_guilhermino import CORPUS as GDA_VERSOS  # noqa: E402

TOKEN = re.compile(r"[a-záàâãéêíóôõúüç]+", re.IGNORECASE)


def tokens_de(texto: str) -> set[str]:
    return {t.lower() for t in TOKEN.findall(texto)}


def coletar_vocabulario() -> Counter:
    contagem: Counter[str] = Counter()
    xmls = sorted(CORPUS.glob("*.xml"))
    if xmls:
        import xml.etree.ElementTree as ET

        ns = "{http://www.tei-c.org/ns/1.0}"
        for caminho in xmls:
            raiz = ET.parse(caminho).getroot()
            for verso in raiz.iter(f"{ns}l"):
                if verso.text:
                    contagem.update(tokens_de(verso.text))
    for versos in GDA_VERSOS.values():
        contagem.update(tokens_de(" ".join(versos)))
    return contagem


def consultar_lt(palavras: list[str]) -> tuple[set[str], set[str]]:
    """Consulta o LT em lote (uma palavra por linha). Devolve (ok, erro)."""
    texto = "\n".join(palavras)
    dados = urllib.parse.urlencode(
        {"text": texto, "language": "pt-BR"}
    ).encode()
    requisicao = urllib.request.Request(LT, data=dados)
    with urllib.request.urlopen(requisicao, timeout=120) as resposta:
        conteudo = json.loads(resposta.read())
    erros: set[str] = set()
    for m in conteudo.get("matches", []):
        if m["rule"].get("issueType") == "misspelling":
            trecho = texto[m["offset"]: m["offset"] + m.get("length", 0)]
            erros.add(trecho.lower().strip())
    ok = {p for p in palavras if p.lower() not in erros}
    return ok, {e for e in erros if e}


def main() -> None:
    contagem = coletar_vocabulario()
    palavras = sorted(contagem)
    print(f"vocabulário bruto: {len(palavras)} tokens únicos")

    validas: set[str] = set()
    rejeitadas: list[tuple[str, int]] = []
    for i in range(0, len(palavras), TAMANHO_LOTE):
        lote = palavras[i:i + TAMANHO_LOTE]
        ok, erro = consultar_lt(lote)
        validas |= ok
        rejeitadas += [(p, contagem[p]) for p in erro]
        feito = min(i + TAMANHO_LOTE, len(palavras))
        print(f"\r{feito}/{len(palavras)}", end="", flush=True)
    print()

    SAIDA.write_text(
        "\n".join(sorted(validas)) + "\n", encoding="utf-8"
    )
    print(f"{len(validas)} válidas -> {SAIDA}")
    raras = [p for p, n in sorted(rejeitadas, key=lambda x: -x[1])[:15]]
    print(f"rejeitadas pelo LT: {len(rejeitadas)}; mais frequentes: {raras}")


if __name__ == "__main__":
    sys.exit(main())
