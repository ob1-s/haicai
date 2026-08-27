"""Gera haikus em massa com frota multi-provedor (variance de modelos).

Provedores:
- Gemini direto (2 chaves de cotas independentes, modelos flash 3.x)
- OpenRouter (:free)
- Nous Portal via proxy Hermes local (127.0.0.1:8645, qualquer bearer)

Cada amostra no JSONL carrega metadados: texto, tema, temperatura,
provedor, modelo e esforco_raciocinio.

    python tools/gera_haikus.py --n 2400 --out data/geracao_bruta.jsonl

Endurecido contra provedor caprichoso: prazo global (--minutos),
socket fechado explicitamente em todo caminho de erro, progresso
visível a cada 10.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URL_GEMINI = (
    "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:"
    "generateContent?key={chave}"
)

# Modelo → thinkingBudget (3.6 exige thinking; 3.5 aceita desligado).
GEMINI = {
    "gemini-3.5-flash": 0,
    "gemini-3.6-flash": 512,
    "gemini-3.7-flash": 0,
}

OPENROUTER = [
    "minimax/minimax-m3:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
]

NOUS = [
    "stealth/ox-alpha",        # balde Stealth instável no pico; volta no off
    "meituan/longcat-2.0:free",
    "upstage/solar-pro4:free",
]

HERMES = os.environ.get("HAICAI_HERMES_URL", "http://127.0.0.1:8645/v1")

TEMAS = """
mar lua chuva cão gato rua café saudade noite manhã vento
ponte pedra folha pássaro sombra fogo areia neblina rio maré
farol jardim janela escada relógio espelho corda vidro ferro
outono verão inverno primavera tempestade calmaria maré baixa
cidade vila praia morro mata campo céu estrela nuvem orvalho
sino barco vela remanso mangue costão gamboa sereno
solidão encontro despedida memória silêncio grito riso choro
infância avó pai mãe filho amigo estranho cão velho
""".split()


def prompt(tema: str) -> str:
    return (
        f"Escreva um haiku original em português brasileiro sobre: {tema}.\n"
        "Regras: 3 linhas, 5-7-5 sílabas poéticas, sem título, sem "
        "pontuação obrigatória, sem numeração, sem comentários.\n"
        "Responda SOMENTE com as três linhas do haiku."
    )


def sanitiza(texto: str | None) -> str | None:
    if not texto:
        return None
    # Modelos com raciocínio às vezes vazam bloco de pensamento.
    if "<think>" in texto:
        inicio = texto.find("<think>")
        fim = texto.find("</think>")
        texto = texto[:inicio] + texto[fim + len("</think>"):] if fim > inicio else ""
        texto = texto.strip()
    return texto.strip() if len(texto.strip().splitlines()) >= 3 else None


def _curl_json(url: str, corpo: bytes, chave: str, prazo: int) -> bytes | None:
    """POST com prazo de parede — urllib já nos traiu 3 vezes hoje."""
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", str(prazo), "-X", "POST", url,
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {chave}",
             "--data-binary", "@-"],
            input=corpo, capture_output=True, timeout=prazo + 5,
        )
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 else None


def chamar_gemini(
    modelo: str, chave: str, tema: str, temperatura: float, budget: int
) -> str | None:
    corpo = json.dumps({
        "contents": [{"parts": [{"text": prompt(tema)}]}],
        "generationConfig": {
            "temperature": temperatura,
            "maxOutputTokens": 300,
            "thinkingConfig": {"thinkingBudget": budget},
        },
    }).encode()
    bruto = _curl_json(
        URL_GEMINI.format(modelo=modelo, chave=chave),
        corpo, chave, prazo=30,
    )
    if not bruto:
        return None
    try:
        dados = json.loads(bruto)
        return sanitiza(dados["candidates"][0]["content"]["parts"][0]["text"])
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


def chamar_chat(
    url_base: str, modelo: str, chave: str, tema: str, temperatura: float
) -> str | None:
    corpo = json.dumps({
        "model": modelo,
        "messages": [{"role": "user", "content": prompt(tema)}],
        "temperature": temperatura,
        # Modelos com raciocínio queimam tokens pensando antes de responder.
        "max_tokens": 2000,
    }).encode()
    bruto = _curl_json(f"{url_base}/chat/completions", corpo, chave, prazo=40)
    if not bruto:
        return None
    try:
        dados = json.loads(bruto)
        return sanitiza(dados["choices"][0]["message"]["content"])
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--out", default="data/geracao_bruta.jsonl")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--minutos", type=float, default=25.0)
    args = parser.parse_args()

    chaves_gemini = [v for k in ("GEMINI_API_KEY", "GEMINI_API_KEY_2")
                     if (v := os.environ.get(k))]
    caminho_env = Path.home() / "Desktop" / ".env"
    chave_or = ""
    if caminho_env.exists():
        for linha in caminho_env.read_text().splitlines():
            if linha.startswith("OPENROUTER_API_KEY"):
                chave_or = linha.split(None, 1)[1].strip()

    frota: list[dict] = []
    for chave, (modelo, budget) in itertools.product(chaves_gemini, GEMINI.items()):
        frota.append({"provedor": "gemini", "modelo": modelo, "chave": chave,
                      "budget": budget})
    if chave_or:
        for modelo in OPENROUTER:
            frota.append({"provedor": "openrouter", "modelo": modelo,
                          "chave": chave_or, "budget": 0})
    for modelo in NOUS:
        frota.append({"provedor": "nous-hermes", "modelo": modelo,
                      "chave": "hermes-local", "budget": 0})
    if not frota:
        sys.exit("nenhum provedor disponível")
    print(f"frota: {len(frota)} combos "
          f"(gemini={len(chaves_gemini)*len(GEMINI)}, "
          f"openrouter={len(OPENROUTER) if chave_or else 0}, "
          f"nous={len(NOUS)}), meta {args.n}", flush=True)

    trava = threading.Lock()
    estado = {"feitas": 0, "falhas": 0}
    prazo = time.monotonic() + args.minutos * 60
    saida = Path(args.out)
    saida.parent.mkdir(parents=True, exist_ok=True)

    def trabalho(i: int) -> None:
        if time.monotonic() > prazo:
            return
        tarefa = frota[i % len(frota)]
        tema = random.choice(TEMAS)
        temperatura = round(random.uniform(0.9, 1.3), 2)
        texto = None
        for tentativa in range(3):
            if time.monotonic() > prazo:
                return
            if tarefa["provedor"] == "gemini":
                texto = chamar_gemini(tarefa["modelo"], tarefa["chave"],
                                      tema, temperatura, tarefa["budget"])
            elif tarefa["provedor"] == "openrouter":
                texto = chamar_chat("https://openrouter.ai/api/v1",
                                    tarefa["modelo"], tarefa["chave"],
                                    tema, temperatura)
            else:
                texto = chamar_chat(HERMES, tarefa["modelo"],
                                    tarefa["chave"], tema, temperatura)
            if texto:
                break
            with trava:
                estado["falhas"] += 1
            time.sleep(min(60, 2 ** tentativa * 4) *
                       random.uniform(0.8, 1.2))
        if not texto:
            return
        with trava:
            with saida.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "texto": texto,
                    "tema": tema,
                    "temperatura": temperatura,
                    "provedor": tarefa["provedor"],
                    "modelo": tarefa["modelo"],
                    "esforco_raciocinio": (
                        str(tarefa["budget"])
                        if tarefa["provedor"] == "gemini" else "padrao"
                    ),
                }, ensure_ascii=False) + "\n")
            estado["feitas"] += 1
            if estado["feitas"] % 10 == 0:
                print(f"{estado['feitas']} ok / {estado['falhas']} falhas",
                      flush=True)

    inicio = time.perf_counter()
    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(trabalho, range(args.n)))
    print(f"\n{estado['feitas']} haikus em "
          f"{time.perf_counter()-inicio:.0f}s -> {saida}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
