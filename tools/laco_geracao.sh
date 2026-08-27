#!/bin/bash
# Laço de geração: ondas de frota até encher o alvo ou acabar a janela.
# Provedor em horário de pico devolve 429/503; off-peak destrava.
cd /home/ob1/Projects/haicai
ALVO=1500
for onda in $(seq 1 16); do
    atual=$(wc -l < data/geracao_bruta.jsonl 2>/dev/null || echo 0)
    echo "[laco] onda $onda | $atual/$ALVO haikus | $(date +%H:%M)"
    if [ "$atual" -ge "$ALVO" ]; then
        echo "[laco] alvo atingido"; break
    fi
    .venv/bin/python tools/gera_haikus.py --n 2400 --workers 9 --minutos 20 \
        --out data/geracao_bruta.jsonl
    sleep 600
done
echo "[laco] fim: $(wc -l < data/geracao_bruta.jsonl) haikus | $(date +%H:%M)"
