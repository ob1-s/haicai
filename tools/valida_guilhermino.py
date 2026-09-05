"""Valida o corpus canônico contra a fórmula do próprio Guilherme de Almeida:
5-7-5, v1 rimando com v3, rima interna no v2 entre as sílabas tônicas 2 e 7.

Uso: .venv/bin/python tools/valida_guilhermino.py
"""
from itertools import product
import unicodedata

from escansao import _aplica, _juncoes, _limpa, _silabas
from haicai import escandir, forma_ok

CORPUS = {
    "VELHICE":   ["Uma folha morta.", "Um galho no céu grisalho.", "Fecho a minha porta."],
    "INFÂNCIA":  ["Um gosto de amora", "comida com sol. A vida", "chamava-se “Agora”."],
    "O HAICAI":  ["Lava, escorre, agita", "a areia. E enfim, na batéia,", "fica uma pepita."],
    "NOTURNO":   ["Na cidade, a lua:", "a jóia branca que bóia", "na lama da rua."],
    "JANEIRO":   ["Jasmineiro em flor.", "Ciranda o luar na varanda.", "Cheiro de calor."],
    "MOCIDADE":  ["Do beiral da casa", "(ó telhas novas, vermelhas!)", "vai-se embora uma asa."],
    "CARIDADE":  ["Desfolha-se a rosa", "parece até que floresce", "o chão cor-de-rosa."],
    "CIGARRA":   ["Diamante. Vidraça.", "Arisca, áspera asa risca", "o ar. E brilha. E passa."],
    "SAUDADE":   ["Houve aquele tempo...", "(E agora, que a chuva chora,", "ouve aquele tempo!)"],
    # Pré-fórmula (Acaso, 1924-28): sem rima, sem 5-7-5 exigido.
    "Bashô GdA": ["Ah! o antigo açude!", "E quando uma rã mergulha,", "o marulho da água."],
    # CASO EM ABERTO: não alcança 7; ver conversa de calibração.
    "GAROA":     ["Por um mundo quase", "o éreo, há um vago mistério.", "Passa o Anjo de Gaze."],
}

PRE_FORMULA = {"Bashô GdA"}


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def chave(s):
    return norm(s.nucleo) + norm(s.glide) + norm(s.coda)


def leituras(verso: str):
    palavras = [p for t in verso.split() if (p := _limpa(t))]
    silabas: list = []
    for i, p in enumerate(palavras):
        silabas.extend(_silabas(p, i))
    js = _juncoes(silabas)
    out = []
    for escolhas in product([False, True], repeat=len(js)):
        seq = _aplica(silabas, escolhas, js)
        n = next((i + 1 for i in range(len(seq) - 1, -1, -1) if seq[i].tonica), len(seq))
        out.append((n, seq))
    return out


def rima_fim(a, b) -> str:
    ta = next((s for s in reversed(a) if s.tonica), None)
    tb = next((s for s in reversed(b) if s.tonica), None)
    if not ta or not tb:
        return "—"
    if chave(ta) == chave(tb):
        return "consoante"
    if norm(ta.nucleo) == norm(tb.nucleo):
        return "toante"
    return "—"


def rima_interna(verso: str):
    melhor = None
    for n, seq in leituras(verso):
        if n == 7 and len(seq) >= 7:
            k2, k7 = chave(seq[1]), chave(seq[6])
            if k2 == k7:
                return "consoante", "·".join(s.texto for s in seq)
            if norm(seq[1].nucleo) == norm(seq[6].nucleo) and melhor is None:
                melhor = ("toante", "·".join(s.texto for s in seq))
    return (melhor[0], melhor[1]) if melhor else ("—", None)


def main() -> None:
    falhas = []
    for titulo, versos in CORPUS.items():
        rs = [escandir(v) for v in versos]
        membro = forma_ok(*rs)["forma_ok"]
        l1, l2, l3 = (leituras(v) for v in versos)
        r13 = max(
            (rima_fim(s1, s3) for _, s1 in l1 for _, s3 in l3),
            key=lambda x: ["—", "toante", "consoante"].index(x),
        )
        rint, lei = rima_interna(versos[1])
        ok = membro and (titulo in PRE_FORMULA or (r13 != "—" and rint != "—"))
        if not ok:
            falhas.append(titulo)
        print(
            f"{'OK' if ok else '!!':3} {titulo:10} "
            f"{'/'.join(str(r.minimo) if r.minimo == r.maximo else f'[{r.minimo}..{r.maximo}]' for r in rs):24} "
            f"1-3: {r13:10} 2/7: {rint:10} {lei or ''}"
        )
    print(f"\n{'tudo ok' if not falhas else 'revisar: ' + ', '.join(falhas)}")


if __name__ == "__main__":
    main()
