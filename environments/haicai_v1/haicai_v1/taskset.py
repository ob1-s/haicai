"""haicai-v1: escrever haicai 5-7-5 em português brasileiro.

Recompensa determinística, sem LLM no loop:
- forma (peso 0.5): fração dos versos cujo intervalo de escansão
  defensável contém o alvo 5/7/5 — crédito parcial por verso;
- ortografia (peso 0.5): cobertura do léxico compilado AO90
  (40k palavras validadas pelo LanguageTool sobre corpus pós-reforma).

Mesma semântica do pacote de hub `haicai` (v0) usado no Hosted RL.
O system_prompt é campo configurável para o GEPA otimizar.
"""
import verifiers.v1 as vf

from haicai.escansao import escandir
from haicai.orto import coverage

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


def _versos(texto: str | None) -> list[str]:
    return [v.strip() for v in (texto or "").splitlines() if v.strip()]


class HaicaiData(vf.TaskData):
    tema: str


class HaicaiTask(vf.Task[HaicaiData]):
    @vf.stop
    async def single_turn(self, trace: vf.Trace) -> bool:
        return trace.num_turns >= 1

    @vf.reward(weight=0.5)
    async def forma(self, trace: vf.Trace) -> float:
        versos = _versos(trace.last_reply)
        if len(versos) != 3:
            return 0.0
        alvos = (5, 7, 5)
        resultados = [escandir(v) for v in versos]
        return sum(
            alvo in range(r.minimo, r.maximo + 1)
            for alvo, r in zip(alvos, resultados)
        ) / 3

    @vf.reward(weight=0.5)
    async def ortografia(self, trace: vf.Trace) -> float:
        return coverage(trace.last_reply or "")

    @vf.metric
    async def exata_575(self, trace: vf.Trace) -> float:
        versos = _versos(trace.last_reply)
        if len(versos) != 3:
            return 0.0
        alvos = (5, 7, 5)
        resultados = [escandir(v) for v in versos]
        return float(
            all(
                alvo in range(r.minimo, r.maximo + 1)
                for alvo, r in zip(alvos, resultados)
            )
        )


class HaicaiConfig(vf.TasksetConfig):
    num_tasks: int = 200
    offset: int = 0
    """Desloca a janela de temas — use para train/test disjuntos."""


class HaicaiTaskset(vf.Taskset[HaicaiTask, HaicaiConfig]):
    def load(self) -> list[HaicaiTask]:
        return [
            HaicaiTask(
                HaicaiData(
                    idx=i,
                    prompt=(
                        f"Escreva um haiku original em português brasileiro "
                        f"sobre: {tema_de(i, self.config.offset)}.\n"
                        "Responda SOMENTE com as três linhas do haiku."
                    ),
                    system_prompt=SYSTEM_PROMPT,
                    tema=tema_de(i, self.config.offset),
                ),
                self.config.task,
            )
            for i in range(self.config.num_tasks)
        ]


def tema_de(i: int, offset: int = 0) -> str:
    return TEMAS[(offset + i) % len(TEMAS)]

__all__ = ["HaicaiTaskset"]
