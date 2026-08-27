"""Escansão de versos em português: sílabas poéticas por hipóteses.

A contagem poética (métrica) difere da gramatical:
- conta-se até a ÚLTIMA SÍLABA TÔNICA do verso (postônicas finais caem);
- SINALEFA: vogal final + vogal inicial de palavra vizinha podem fundir;
- SINÉRESE: hiato interno pode fundir (sinfonia: sin-fo-ni-a -> sin-fo-nia);
- DIÉRESE: ditongo átono pode romper (traição: trai-ção -> tra-i-ção).

Como várias dessas fusões são escolhas rítmicas, devolvemos um INTERVALO
[min, max] de contagens defensáveis, não um único número.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from silabificador import analyze, stressed_index

# Palavras átonas: não carregam a última tônica do verso.
ATONOS = frozenset("""
    o a os as um uma uns umas
    de do da dos das no na nos nas em ao à aos às
    pelo pela pelos pelas por com sem sob per ante
    me te se lhe lhes nos vos
    e ou nem que se
""".split())

# Pronomes enclíticos: em fá-lo-ias a tônica fica em FÁ, não no clítico.
CLITICOS = frozenset("""
    o a os as lo la los las no na nos nas
    mo ma to ta lho lha lhos lhas nho nha
    lhe lhes me te se nos vos
""".split())

# Desinências verbais de mesóclise (fá-lo-ias, amar-te-ia).
FINS_VERBAIS = frozenset("ia ias ieis iam á ao ão eis am ás".split())

# Vogais altas podem vir glide mesmo tônicas (sinfonia: ni|a -> nia)
VOGAIS = frozenset("aeiouáéíóúâêôãõà")
ALTAS = frozenset("iíuú")
NASAIS = frozenset("ãõ")

MAX_JUNCOES = 14


@dataclass
class Silaba:
    texto: str
    nucleo: str
    glide: str
    coda: str
    onset: str
    tonica: bool
    palavra: int


@dataclass
class Hipotese:
    contagem: int
    silabas: list[str]
    fusoes: tuple[str, ...] = ()


@dataclass
class Resultado:
    linha: str
    minimo: int
    maximo: int
    hipoteses: list[Hipotese]
    aviso: str = ""

    @property
    def largura(self) -> int:
        return self.maximo - self.minimo


def _limpa(t: str) -> str:
    return t.strip(".,;:!?—–«»\"'“”‘’()[]{}…").lower()


def _silabas(palavra: str, idx: int) -> list[Silaba]:
    partes = [analyze(p) for p in palavra.split("-")]
    elementos = ["".join(str(x) for x in parte) for parte in partes]
    enclitico = "-" in palavra and all(
        e in CLITICOS or (i == len(elementos) - 1 and e in FINS_VERBAIS)
        for i, e in enumerate(elementos[1:], 1)
    )

    saida: list[Silaba] = []
    for i, parte in enumerate(partes):
        for syl in parte:
            tonica = syl.stressed and not (enclitico and i > 0)
            saida.append(Silaba(
                texto=str(syl).strip("'- "),
                nucleo=syl.nucleus,
                glide=syl.glide_off,
                coda=syl.coda,
                onset=syl.onset,
                tonica=tonica,
                palavra=idx,
            ))
    if enclitico:
        saida[stressed_index(elementos[0])].tonica = True
    if palavra in ATONOS:
        for s in saida:
            s.tonica = False
    return saida


def _vogal_final(s: Silaba) -> bool:
    if not s.nucleo or s.glide:
        return False
    if s.coda == "":
        return True
    # nasal: vogal + m/n(s) fecha sem oclusão e liga à vogal seguinte
    # ("viveram em" -> vi·ve·rem·paz; tratado do Recanto das Letras)
    t = s.texto.lower()
    return (
        len(t) >= 2
        and t[-1] in "mn"
        and t[-2] in VOGAIS
        or len(t) >= 3
        and t[-1] == "s"
        and t[-2] == "n"
        and t[-3] in VOGAIS
    )


def _vogal_inicial(s: Silaba) -> bool:
    return s.onset in ("", "h")


def _juncoes(silabas: list[Silaba]) -> list[dict]:
    tam_por_palavra: dict[int, int] = {}
    for s in silabas:
        tam_por_palavra[s.palavra] = tam_por_palavra.get(s.palavra, 0) + 1

    # pós-tônica: não-tônica cuja palavra já teve tônica ("viveram": ram)
    tonica_vista: set[int] = set()
    pos_tonica: list[bool] = []
    for s in silabas:
        pos_tonica.append(s.palavra in tonica_vista)
        if s.tonica:
            tonica_vista.add(s.palavra)

    js: list[dict] = []
    for i, s in enumerate(silabas):
        prox = silabas[i + 1] if i + 1 < len(silabas) else None
        mesma = prox is not None and s.palavra == prox.palavra
        if s.glide and not s.tonica and s.nucleo not in NASAIS:
            js.append({"idx": i, "tipo": "dierese"})
        if prox is not None and mesma and s.glide and _vogal_inicial(prox) and (s.glide == "i" or not s.tonica):
            # sinérese de ditongo + vogal: areia -> a-reia, jóia -> jóia
            js.append({"idx": i, "tipo": "sinerese"})
        if prox is not None and _vogal_final(s) and _vogal_inicial(prox):
            if mesma:
                # sinérese: átona à esquerda, ou núcleo alto que vira glide
                if not s.tonica or s.nucleo in ALTAS:
                    js.append({"idx": i, "tipo": "sinerese"})
            else:
                # sinalefa: átona à esquerda, vogais iguais, núcleo alto,
                # ou monossílabo tônico oxítono (há|um -> haum) — a
                # "sinalefa forçada" de Amorim de Carvalho, Tratado de
                # Versificação Portuguesa: rara, mas técnica reconhecida.
                if (
                    not s.tonica
                    or s.nucleo in ALTAS
                    or s.nucleo == prox.nucleo
                    or (s.tonica and tam_por_palavra[s.palavra] == 1)
                    # pós-tônica à esquerda: "viveram em" -> vi·ve·rem·paz
                    # (sinalefa extrema do tratado do Recanto das Letras)
                    or pos_tonica[i]
                ):
                    js.append({"idx": i, "tipo": "sinalefa"})
    return js


def _aplica(silabas: list[Silaba], escolhas, juncoes) -> list[Silaba]:
    ops_por_idx: dict[int, list[tuple[dict, bool]]] = {}
    for j, e in zip(juncoes, escolhas):
        ops_por_idx.setdefault(j["idx"], []).append((j, e))

    saida: list[Silaba] = []
    i = 0
    while i < len(silabas):
        s = silabas[i]
        ops = ops_por_idx.get(i, [])
        dierese = next((j for j, e in ops if j["tipo"] == "dierese" and e), None)
        fusao = next((j for j, e in ops if j["tipo"] in ("sinerese", "sinalefa") and e), None)
        if dierese:
            saida.append(Silaba(s.texto[: -len(s.glide)], s.nucleo, "", "", s.onset, s.tonica, s.palavra))
            saida.append(Silaba(s.glide, s.glide, "", "", "", False, s.palavra))
            i += 1
        elif fusao:
            p = silabas[i + 1]
            texto, tonica = s.texto + p.texto, s.tonica or p.tonica
            glide, coda, fim = s.glide or p.glide, p.coda, i + 1
            # cadeia de sinalefas: "passa o anjo" -> pas·saoan·jo
            while True:
                elo = next(
                    (j for j, e in ops_por_idx.get(fim, []) if e and j["tipo"] in ("sinerese", "sinalefa")),
                    None,
                )
                if elo is None or fim + 1 >= len(silabas):
                    break
                nxt = silabas[fim + 1]
                texto += nxt.texto
                tonica = tonica or nxt.tonica
                glide = glide or nxt.glide
                coda = nxt.coda
                fim += 1
            saida.append(Silaba(texto, s.nucleo, glide, coda, s.onset, tonica, s.palavra))
            i = fim + 1
        else:
            saida.append(s)
            i += 1
    return saida


def _conta(seq: list[Silaba]) -> int:
    for i in range(len(seq) - 1, -1, -1):
        if seq[i].tonica:
            return i + 1
    return len(seq)


def escandir(linha: str) -> Resultado:
    palavras = [p for t in linha.split() if (p := _limpa(t))]
    if not palavras:
        return Resultado(linha, 0, 0, [], "linha vazia")

    silabas: list[Silaba] = []
    for idx, p in enumerate(palavras):
        silabas.extend(_silabas(p, idx))

    juncoes = _juncoes(silabas)
    aviso = ""
    if len(juncoes) > MAX_JUNCOES:
        juncoes = juncoes[:MAX_JUNCOES]
        aviso = f"limitado a {MAX_JUNCOES} junções"

    hipoteses: dict[int, Hipotese] = {}
    for escolhas in product([False, True], repeat=len(juncoes)):
        seq = _aplica(silabas, escolhas, juncoes)
        n = _conta(seq)
        if n not in hipoteses:
            fusoes = tuple(j["tipo"] for j, e in zip(juncoes, escolhas) if e)
            hipoteses[n] = Hipotese(n, [s.texto for s in seq], fusoes)

    contagens = sorted(hipoteses)
    return Resultado(linha, contagens[0], contagens[-1], [hipoteses[n] for n in contagens], aviso)


def forma_ok(v1: Resultado, v2: Resultado, v3: Resultado, largura_max: int | None = None) -> dict:
    """Portão binário do haicai 5-7-5 (por intervalo de contagens defensáveis)."""
    alvos = (5, 7, 5)
    dentro = [alvo in range(r.minimo, r.maximo + 1) for alvo, r in zip(alvos, (v1, v2, v3))]
    largura_ok = True if largura_max is None else max(r.largura for r in (v1, v2, v3)) <= largura_max
    return {"forma_ok": all(dentro) and largura_ok, "versos_ok": dentro, "largura_ok": largura_ok}
