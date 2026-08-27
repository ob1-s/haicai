"""Uso: python -m haicai "verso 1" "verso 2" "verso 3"  (ou versos via stdin)."""
import sys

from haicai import escandir, forma_ok


def main() -> None:
    versos = sys.argv[1:] or [line.strip() for line in sys.stdin if line.strip()]
    resultados = [escandir(v) for v in versos]
    for r in resultados:
        print(f"\n{r.linha!r}  ->  [{r.minimo}..{r.maximo}]  (largura {r.largura})")
        for h in r.hipoteses:
            fusoes = f"   [{' '.join(h.fusoes)}]" if h.fusoes else ""
            print(f"   {h.contagem:2d}  {'·'.join(h.silabas)}{fusoes}")
    if len(resultados) == 3:
        print(f"\n5-7-5? {forma_ok(*resultados)}")


if __name__ == "__main__":
    main()
