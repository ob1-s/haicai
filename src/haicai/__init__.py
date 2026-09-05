"""Kit do projeto haicai sobre o motor geral `escansao` (PyPI/git).

- escansão (intervalos): `escandir, Resultado, Hipotese` re-exportados de `escansao`;
- forma 5-7-5: `forma_ok` (este projeto);
- ortografia AO90: `coverage, vocabulario` (léxico compilado do projeto),
  `ortografia` (cliente do sidecar LanguageTool, só para tooling offline).
"""
from escansao import Hipotese, Resultado, escandir

from haicai.forma import forma_ok
from haicai.orto import coverage, vocabulario

__all__ = ["escandir", "forma_ok", "Resultado", "Hipotese", "coverage", "vocabulario"]
