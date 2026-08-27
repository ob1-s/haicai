"""UI de rating do love bank: love / ok / nope em haikus pré-filtrados.

Serve apenas amostras de data/geracao_bruta.jsonl que passam pelos dois
gates (forma_ok 5-7-5 + ortografia). Rating às cegas: nada de modelo ou
provedor na tela — o juízo não pode saber quem escreveu. Cada voto vai
para data/rating.jsonl com hash do texto como id.

Uso: .venv/bin/python tools/anota_love.py   ->  http://localhost:8766
"""
import hashlib
import json
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from haicai import ortografia
from haicai.escansao import escandir, forma_ok

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "data" / "geracao_bruta.jsonl"
LOG = RAIZ / "data" / "rating.jsonl"
PORTA = 8766

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>love bank &middot; rating</title>
<style>
 body{font-family:Georgia,serif;max-width:40em;margin:3em auto;padding:0 1em;background:#faf7f0;color:#222;text-align:center}
 h1{font-size:1.1em;font-weight:normal;border-bottom:1px solid #ccc;padding-bottom:.4em}
 #haiku{font-size:1.7em;font-style:italic;margin:2em 0;white-space:pre-line;min-height:5em}
 button{font-size:1.05em;margin:.4em;padding:.7em 1.6em;border-radius:8px;border:1px solid #bbb;background:#fff;cursor:pointer}
 button:hover{background:#eee}
 #love{border-color:#c9a}#ok{border-color:#bb8}#nope{border-color:#999}#pula{font-size:.85em;color:#777}
 #progresso{color:#999;font-size:.85em;margin-top:2em}
</style></head><body>
<h1>love bank &mdash; esse haiku te comove?</h1>
<div id="haiku">carregando&hellip;</div>
<div>
 <button id="love" onclick="vota('love')">love (1)</button>
 <button id="ok" onclick="vota('ok')">ok (2)</button>
 <button id="nope" onclick="vota('nope')">nope (3)</button>
</div>
<button id="pula" onclick="proximo()">pular &middot; p</button>
<button id="pula" onclick="desfazer()">desfazer &middot; z</button>
<div id="progresso"></div>
<script>
let atual = null;
let anterior = null;
const teclas = {Digit1:'love', Digit2:'ok', Digit3:'nope', KeyP:'pular', KeyZ:'desfazer'};
async function proximo() {
  const r = await fetch('/proximo');
  const d = await r.json();
  if (!d.id) { document.getElementById('haiku').textContent = 'acabou o estoque — espere a frota'; return; }
  anterior = atual && atual.id ? atual : anterior;
  atual = d;
  document.getElementById('haiku').textContent = d.texto;
  document.getElementById('progresso').textContent =
    `votos: ${d.votados} · estoque: ${d.estoque}`;
}
async function vota(nota) {
  if (!atual) return;
  await fetch('/resposta', {method:'POST', headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({id: atual.id, nota})});
  proximo();
}
async function desfazer() {
  if (!anterior) return;
  await fetch('/resposta', {method:'POST', headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({id: anterior.id, nota:'anular'})});
  atual = anterior;
  const r = await fetch('/proximo');
  const d = await r.json();
  document.getElementById('haiku').textContent = anterior.texto;
  document.getElementById('progresso').textContent =
    `votos: ${d.votados} · estoque: ${d.estoque}`;
  anterior = null;
}
document.addEventListener('keydown', e => {
  if (teclas[e.code] === 'pular' || teclas[e.code] === 'desfazer') {
    ({pular: proximo, desfazer})[teclas[e.code]]();
  } else if (teclas[e.code]) vota(teclas[e.code]);
});
proximo();
</script>
</body></html>"""


def hash_de(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


def elegiveis() -> list[dict]:
    """Amostras que passam forma + ortografia, sem repetição de texto."""
    vistos: dict[str, dict] = {}
    if FONTE.exists():
        for linha in FONTE.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            d = json.loads(linha)
            versos = [v.strip() for v in d["texto"].splitlines() if v.strip()]
            if len(versos) != 3:
                continue
            if not forma_ok(*[escandir(v) for v in versos])["forma_ok"]:
                continue
            if not ortografia.gate_rapido(d["texto"])[0]:
                continue
            h = hash_de("\n".join(versos))
            if h not in vistos:
                vistos[h] = {"id": h, "texto": "\n".join(versos)}
    return list(vistos.values())


def votados() -> set[str]:
    """Ids com voto vigente — 'anular' devolve a amostra ao estoque."""
    if not LOG.exists():
        return set()
    ultimo: dict[str, str] = {}
    for l in LOG.read_text(encoding="utf-8").splitlines():
        if l.strip():
            d = json.loads(l)
            ultimo[d["id"]] = d["nota"]
    return {i for i, n in ultimo.items() if n != "anular"}


class Handler(BaseHTTPRequestHandler):
    def _html(self, corpo: str, tipo: str = "text/html; charset=utf-8") -> None:
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.end_headers()
        self.wfile.write(corpo.encode())

    def log_message(self, *a) -> None:
        pass

    def do_GET(self):
        if self.path == "/":
            self._html(PAGINA)
        elif self.path == "/proximo":
            ja_votados = votados()
            estoque = [h for h in elegiveis() if h["id"] not in ja_votados]
            escolha = random.choice(estoque) if estoque else {}
            escolha["votados"] = len(ja_votados)
            escolha["estoque"] = len(estoque)
            self._html(json.dumps(escolha, ensure_ascii=False),
                       "application/json")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/resposta":
            tamanho = int(self.headers.get("Content-Length", 0))
            dados = json.loads(self.rfile.read(tamanho))
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": dados.get("id"),
                    "nota": dados.get("nota"),
                }, ensure_ascii=False) + "\n")
            self._html("{}", "application/json")
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    servidor = HTTPServer(("0.0.0.0", PORTA), Handler)
    print(f"rating em http://localhost:{PORTA} (e http://10.252.77.30:{PORTA} na rede) — love/ok/nope, às cegas")
    servidor.serve_forever()
