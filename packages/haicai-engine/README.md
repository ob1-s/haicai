# haicai — deterministic Portuguese haiku engine

Zero-dependency scansion + orthography coverage for Brazilian-Portuguese 5-7-5.

```python
from haicai import escandir, forma_ok, coverage

r = escandir("No meio do caminho")  # Resultado(minimo=5, maximo=6, ...)
forma_ok(*[escandir(v) for v in verso1, verso2, verso3])
coverage("Vento frio na rua\nFolhas secas no chão\nNoite cai sem lua")
```

- `escandir(linha)` returns an interval `[min, max]` of defensible poetic-syllable
  counts (sinalefa, sinérese, diérese, post-tonic drop, átona demotion, mesóclise),
  not a single number. The interval is where aesthetics lives.
- `coverage(texto)` is the fraction of tokens in the frozen AO90 vocabulary
  (40k words validated by LanguageTool over a post-reform corpus). Continuous in
  [0, 1] — a smooth RL gradient, no Java, no LLM in the loop.

## Attribution

Syllabification base: [silabificador](https://github.com/TigreGotico/silabificador)
(MIT), vendored as `haicai._silabificador`. Vocabulary compiled with LanguageTool 6.4
(pt-BR) — see `tools/compila_vocabulario.py` in the lab repo.
