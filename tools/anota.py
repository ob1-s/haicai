"""UI primordial de anotação: o seu ouvido contra o motor, em versos reais.

Serve uma página local com versos sorteados do corpus UFSC/Aoidos
(poemas nunca vistos por nós dois). Para cada verso mostra as hipóteses
do motor; você marca qual contagem o seu ouvido aceita, quais fusões são
forçadas, e cada resposta vai para data/anotacao.jsonl.

Uso: .venv/bin/python tools/anota.py   ->  http://localhost:8765
"""
import json
import random
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from haicai import escandir

CORPUS = Path("/tmp/opencode/surya/poemas")
LOG = Path(__file__).parent.parent / "data" / "anotacao.jsonl"
PORTA = 8765

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>anota&ccedil;&atilde;o &middot; escans&atilde;o</title>
<style>
 body{font-family:Georgia,serif;max-width:44em;margin:3em auto;padding:0 1em;background:#faf7f0;color:#222}
 h1{font-size:1.2em;font-weight:normal;border-bottom:1px solid #ccc;padding-bottom:.4em}
 .verso{font-size:1.5em;margin:1.2em 0;font-style:italic}
 .meta{color:#777;font-size:.85em}
 .hip{margin:.9em 0;padding:.6em .9em;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer}
 .hip:hover{border-color:#888;background:#fdfbf5}
 .hip b{font-size:1.25em}
 .fusoes{color:#a05a00;font-size:.85em;display:block;margin-top:.25em}
 .botoes{margin-top:1.5em}
 button{font-family:inherit;font-size:1em;padding:.45em 1.1em;margin-right:.5em;border-radius:6px;
        border:1px solid #999;background:#fff;cursor:pointer}
 button.primario{background:#2e5d34;color:#fff;border-color:#2e5d34}
 #status{margin-left:1em;color:#555}
 .aviso{color:#a00;font-size:.9em}
</style></head><body>
<h1>smell test &mdash; escans&atilde;o em versos reais <span class="meta">(corpus UFSC)</span></h1>
<div id="conteudo"><p class="meta">carregando&hellip;</p></div>
<div class="botoes">
 <button id="pular">pular</button>
 <button id="salvar" class="primario">salvar resposta</button>
 <span id="status"></span>
</div>
<script>
let atual=null, aceita=null, forçadas=new Set();
const $=id=>document.getElementById(id);

async function proximo(){
  const r=await fetch('/proximo'); atual=await r.json();
  aceita=null; forçadas.clear(); render();
}

function render(){
  const c=$('conteudo');
  let h=`<p class="verso">${atual.verso}</p>`;
  h+=`<p class="meta">motor: [${atual.minimo}..${atual.maximo}] ${atual.aviso||''}</p>`;
  atual.hipoteses.forEach((hp,i)=>{
    const marcada=aceita===i?' style="border-color:#2e5d34;background:#eef4ee"':'';
    h+=`<div class="hip" data-i="${i}"${marcada}><b>${hp.contagem}</b> &nbsp; ${hp.silabas}`;
    if(hp.fusoes.length) h+=`<span class="fusoes">fusões: ${hp.fusoes.join(' + ')}</span>`;
    h+=`</div>`;
  });
  c.innerHTML=h;
  document.querySelectorAll('.hip').forEach(el=>el.onclick=()=>{
    aceita=+el.dataset.i; render();
  });
}

$('salvar').onclick=async()=>{
  if(aceita===null){ $('status').textContent='marca uma leitura primeiro'; return; }
  await fetch('/resposta',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({verso:atual.verso,aceita:aceita,minimo:atual.minimo,maximo:atual.maximo})});
  $('status').textContent='salvo ✓'; proximo();
};
$('pular').onclick=()=>{ $('status').textContent=''; proximo(); };
proximo();
</script></body></html>"""


def _versos() -> list[str]:
    versos = []
    for f in sorted(CORPUS.glob("*.xml")):
        try:
            raiz = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for l in raiz.iter("{http://www.tei-c.org/ns/1.0}l"):
            texto = " ".join("".join(l.itertext()).split())
            if 30 <= len(texto) <= 70:
                versos.append(texto)
    return versos


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        corpo = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/":
            pagina = PAGINA.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(pagina)))
            self.end_headers()
            self.wfile.write(pagina)
        elif self.path == "/proximo":
            while True:
                verso = random.choice(Handler.versos)
                r = escandir(verso)
                if not r.aviso:
                    break
            self._json({
                "verso": verso,
                "minimo": r.minimo,
                "maximo": r.maximo,
                "aviso": r.aviso,
                "hipoteses": [
                    {"contagem": h.contagem, "silabas": "·".join(h.silabas), "fusoes": h.fusoes}
                    for h in r.hipoteses
                ],
            })
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/resposta":
            self.send_error(404)
            return
        dados = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(dados, ensure_ascii=False) + "\n")
        self._json({"ok": True})

    def log_message(self, *a):
        pass


def main() -> None:
    Handler.versos = _versos()
    print(f"{len(Handler.versos)} versos no baralho -> http://localhost:{PORTA}  (Ctrl+C sai)")
    HTTPServer(("127.0.0.1", PORTA), Handler).serve_forever()


if __name__ == "__main__":
    main()
