"""haicai: escrever haicai 5-7-5 em português brasileiro (Hosted RL).

Recompensa determinística, sem LLM no loop:
- forma (peso 0.5): fração dos versos cujo intervalo de escansão
  defensável contém o alvo 5/7/5 — crédito parcial por verso;
- ortografia (peso 0.5): cobertura do léxico compilado AO90
  (40k palavras validadas pelo LanguageTool sobre corpus pós-reforma).

Pacote autossuficiente: silabificador MIT vendado + vocabulário em
data/. Mesma semântica do taskset v1 `haicai-v1` usado em eval/GEPA.
"""
import random

import verifiers as vf

from haicai_vendor import escansao as esc
from haicai_vendor import orto

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

SYSTEM_PROMPT = (
    "Escreva haikus em português brasileiro. Um haiku tem três versos "
    "de 5, 7 e 5 sílabas poéticas — conta-se até a última sílaba "
    "tônica de cada verso e vogais entre palavras vizinhas podem "
    "fundir. Sem título, sem rima obrigatória. Ortografia correta "
    "pelo Acordo Ortográfico de 1990."
)

ALVOS = (5, 7, 5)


def _versos(texto: str | None) -> list[str]:
    return [v.strip() for v in (texto or "").splitlines() if v.strip()]


def forma_reward(completion: str, **kwargs) -> float:
    versos = _versos(completion)
    if len(versos) != 3:
        return 0.0
    resultados = [esc.escandir(v) for v in versos]
    return sum(
        alvo in range(r.minimo, r.maximo + 1)
        for alvo, r in zip(ALVOS, resultados)
    ) / 3


def ortografia_reward(completion: str, **kwargs) -> float:
    return orto.coverage(completion)


def exata_575_metric(completion: str, **kwargs) -> float:
    return float(forma_reward(completion) == 1.0)


def load_environment(
    num_tasks: int = 500,
    seed: int = 17,
    system_prompt: str | None = SYSTEM_PROMPT,
) -> vf.Environment:
    def build_dataset():
        rng = random.Random(seed)
        linhas = []
        for i in range(num_tasks):
            tema = TEMAS[rng.randrange(len(TEMAS))]
            linhas.append(
                {
                    "question": (
                        f"Escreva um haiku original em português brasileiro "
                        f"sobre: {tema}.\nResponda SOMENTE com as três "
                        "linhas do haiku."
                    ),
                    "answer": "",
                    "info": {},
                }
            )
        import datasets

        return datasets.Dataset.from_list(linhas)

    rubric = vf.Rubric(
        funcs=[forma_reward, ortografia_reward, exata_575_metric],
        weights=[0.5, 0.5, 0.0],
    )

    return vf.SingleTurnEnv(
        dataset=build_dataset,
        system_prompt=system_prompt,
        rubric=rubric,
    )
