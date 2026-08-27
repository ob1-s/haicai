"""Mede cobertura do vocabulário ortográfico sobre haikus gerados.

Entrada: data/geracao_bruta.jsonl (saída de tools/gera_haikus.py).
Responde: que fração dos haikus cai fora do vocabulário compilado,
quantos tokens desconhecidos são erros reais vs. palavras válidas fora
do corpus, e de quebra a taxa de forma_ok (5-7-5) por modelo.

    python tools/mede_ortografia.py [caminho.jsonl]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from haicai import ortografia
from haicai.escansao import escandir, forma_ok


def avalia(linha: str) -> dict:
    d = json.loads(linha)
    texto = d["texto"]
    versos = [v.strip() for v in texto.splitlines() if v.strip()]
    ok, _problemas = ortografia.gate_rapido(texto)
    resultado = {
        "modelo": d["modelo"],
        "provedor": d.get("provedor", "?"),
        "linhas": len(versos),
        "desconhecidas": ortografia.tokens_desconhecidos(texto),
        "orto_ok": ok,
    }
    if len(versos) == 3:
        leituras = [escandir(v) for v in versos]
        resultado["forma"] = forma_ok(*leituras)["forma_ok"]
    return resultado


def main() -> None:
    caminho = Path(sys.argv[1] if len(sys.argv) > 1
                   else RAIZ / "data" / "geracao_bruta.jsonl")
    linhas = [l for l in caminho.read_text(encoding="utf-8").splitlines() if l]
    print(f"{len(linhas)} haikus em {caminho.name}")

    with ThreadPoolExecutor(8) as ex:
        resultados = list(ex.map(avalia, linhas))

    n = len(resultados)
    tres_linhas = [r for r in resultados if r["linhas"] == 3]
    com_forma = [r for r in tres_linhas if r.get("forma")]
    fora_vocab = [r for r in resultados if r["desconhecidas"]]

    print(f"\n== forma (5-7-5) ==")
    print(f"3 linhas: {len(tres_linhas)}/{n} ({len(tres_linhas)/n:.0%})")
    if tres_linhas:
        print(f"forma_ok: {len(com_forma)}/{len(tres_linhas)} "
              f"({len(com_forma)/len(tres_linhas):.0%})")
        por_modelo = Counter(r["modelo"] for r in tres_linhas)
        ok_modelo = Counter(r["modelo"] for r in com_forma)
        for modelo, total_m in sorted(por_modelo.items()):
            print(f"  {modelo}: forma_ok={ok_modelo[modelo]}/{total_m}")

    print(f"\n== ortografia ==")
    print(f"haikus 100% no vocabulário: {n - len(fora_vocab)}/{n} "
          f"({(n - len(fora_vocab))/n:.0%})")
    tokens = Counter(
        t.lower() for r in fora_vocab for t in r["desconhecidas"]
    )
    print(f"tokens desconhecidos únicos: {len(tokens)} "
          f"(ocorrências: {sum(tokens.values())})")

    # Veredito do oráculo (gate_rapido consultou o LT no fallback).
    validas, quebradas = [], []
    for token in tokens:
        (validas if ortografia._vereditos.get(token) else quebradas).append(token)
    auditadas = len(validas) + len(quebradas)
    print(f"\nveredito LT ({auditadas} auditadas): "
          f"{len(validas)} válidas-fora-do-corpus, {len(quebradas)} erros reais")
    print(f"  válidas (amostra): {sorted(validas)[:20]}")
    print(f"  erros    (amostra): {sorted(quebradas)[:20]}")

    custo_fallback = len(ortografia._vereditos)
    print(f"\ncusto total do fallback: {custo_fallback} consultas LT "
          f"para {n} haikus")


if __name__ == "__main__":
    main()
