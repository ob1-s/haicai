"""Sessão de calibração: o seu ouvido contra o motor.

Mostra cada verso com as leituras do motor; tu respondes quais contagens o
seu ouvido aceita. Cada resposta é gravada em data/calibracao.jsonl.

Uso: .venv/bin/python tools/calibra.py [arquivo_batch.json]
"""
import json
import sys
from pathlib import Path

from haicai import escandir

LOG = Path(__file__).parent.parent / "data" / "calibracao.jsonl"


def carregar_respondidos() -> set[str]:
    if not LOG.exists():
        return set()
    return {json.loads(l)["verso"] for l in LOG.read_text().splitlines() if l.strip()}


def gravar(registro: dict) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main() -> None:
    batch = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "data" / "calibracao_v0.json")
    itens = json.loads(batch.read_text())
    respondidos = carregar_respondidos()
    pendentes = [i for i in itens if i["verso"] not in respondidos]

    print(f"{len(itens)} itens, {len(itens) - len(pendentes)} já respondidos, {len(pendentes)} pendentes.")
    print("Respostas: contagens aceitas separadas por espaço (ex: '5 6'),")
    print("  '?' = indeciso, '!' = motor errado de outro jeito, 'sair' = encerrar.\n")

    for n, item in enumerate(pendentes):
        r = escandir(item["verso"])
        print(f"── [{n + 1}/{len(pendentes)}] {item['fenomeno']}")
        print(f"   {item['verso']!r}")
        for h in r.hipoteses:
            fusoes = f"  [{' + '.join(h.fusoes)}]" if h.fusoes else ""
            print(f"     {h.contagem:2d}  {'·'.join(h.silabas)}{fusoes}")
        print(f"   motor: [{r.minimo}..{r.maximo}]  largura {r.largura}")

        try:
            resp = input("   ouvido> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nencerrado.")
            return
        if resp == "sair":
            return

        if resp == "?":
            ouvido, nota = "?", ""
        elif resp == "!":
            ouvido = "!"
            nota = input("   o que está errado? ").strip()
        else:
            try:
                ouvido = sorted({int(x) for x in resp.split()})
                nota = input("   nota (enter p/ pular): ").strip()
            except ValueError:
                print("   (não entendi — item pulado, responde de novo na próxima)")
                continue

        gravar({
            "verso": item["verso"],
            "fenomeno": item["fenomeno"],
            "motor": [r.minimo, r.maximo],
            "hipoteses": [h.contagem for h in r.hipoteses],
            "ouvido": ouvido,
            "nota": nota,
        })
        print()

    print("fim da fila. Obrigado!")


if __name__ == "__main__":
    main()
