# haicai (v0) — DEPRECATED

> This package is the legacy `v0` loader (`load_environment` → `SingleTurnEnv`) that Ox built overnight because the skill text claimed Hosted Training only supported `v0`. The live docs at `docs.primeintellect.ai/hosted-training/advanced-configs` confirm Hosted Training accepts both shapes — `v1` is now canonical.

**Use `environments/haicai_v1` (`ob1/haicai-v1`) instead.** It has the same vendored engine (`silabificador` MIT + `escansao` + `orto` + 40k vocab) and identical rewards (`forma 0.5 / ortografia 0.5`), but as a typed `vf.Taskset` that works for `uv run eval`, `uv run gepa`, and Hosted Training via `taskset = { id = "ob1/haicai-v1" }`.

Kept for reference until `ob1/haicai` hub runs finish. Do not extend — fork `haicai_v1`.
