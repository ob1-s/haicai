"""Valida o motor contra contagens de referência EXTERNA (especialistas).

Cada verso de data/ouro_externo.json tem a contagem atribuída por fonte
autorizada (Ciberdúvidas/ISCTE-IUL, Amorim de Carvalho via Recanto das
Letras, manuais de vestibular). O motor passa se a contagem de ouro cai
dentro do intervalo [min, max] de leituras defensáveis.

Uso: .venv/bin/python tools/valida_ouro.py
"""
import json
from pathlib import Path

from haicai import escandir

OURO = Path(__file__).parent.parent / "data" / "ouro_externo.json"


def main() -> None:
    dados = json.loads(OURO.read_text())
    falhas = []
    fora = 0
    for item in dados["itens"]:
        if item.get("status") == "fora_do_escopo":
            fora += 1
            print(f"--  [{item['verso']}] fora do escopo: {item.get('nota_fonte', '')}")
            continue
        r = escandir(item["verso"])
        alvos = item["ouro"] if isinstance(item["ouro"], list) else [item["ouro"]]
        dentro = [a in range(r.minimo, r.maximo + 1) for a in alvos]
        ok = all(dentro)
        if not ok:
            falhas.append(item)
        marca = "OK " if ok else "!! "
        alvo_str = "/".join(str(a) for a in alvos)
        print(f"{marca}[{r.minimo:2d}..{r.maximo:2d}] ouro={alvo_str:4} {item['verso']!r}")
        if not ok:
            for h in r.hipoteses:
                fusoes = f"  [{' + '.join(h.fusoes)}]" if h.fusoes else ""
                print(f"      {h.contagem:2d}  {'·'.join(h.silabas)}{fusoes}")
            print(f"      fonte: {item['fonte']} — {item.get('nota_fonte', '')}")
    n = len(dados["itens"]) - fora
    print(f"\n{len(dados['itens']) - fora - len(falhas)}/{n} ok" + (f"; {fora} fora do escopo" if fora else "") + (f"; revisar: {len(falhas)}" if falhas else ""))


if __name__ == "__main__":
    main()
