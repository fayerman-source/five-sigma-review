"""Attorney labeling page: Eli codes the held-out test documents BEFORE any model output is shown.
Keys: r = responsive, n = not responsive, 1/2/3 = request, p = privileged toggle, Enter = save & next."""
import json
from pathlib import Path
from flask import Flask, send_file, request, jsonify

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "eval" / "labels.json"
DOCS = [json.loads(l)["doc_id"] for l in (ROOT / "data" / "emails.jsonl").open()]
app = Flask(__name__)

def load():
    return json.loads(LABELS.read_text()) if LABELS.exists() else {}

PAGE = """<!doctype html><meta charset=utf-8><title>Label</title>
<style>body{font:16px system-ui;margin:0;display:flex;height:100vh}#l{flex:1;overflow:auto;background:#333}#l img{width:100%}
#r{width:360px;padding:16px}button{font-size:18px;margin:4px;padding:8px 14px}.on{background:#2a7;color:#fff}</style>
<div id=l><img id=img></div><div id=r><h2 id=t></h2><p id=prog></p>
<div><b>Responsive</b><br><button id=br onclick="set('responsive',true)">Responsive (r)</button><button id=bn onclick="set('responsive',false)">Not (n)</button></div>
<div><b>Request</b><br><button id=b1 onclick="set('request','R1')">R1 (1)</button><button id=b2 onclick="set('request','R2')">R2 (2)</button><button id=b3 onclick="set('request','R3')">R3 (3)</button></div>
<div><b>Privileged</b><br><button id=bp onclick="toggle()">Privileged (p)</button></div>
<p><button onclick="save()">Save &amp; next (Enter)</button> <button onclick="go(-1)">Back</button></p>
<pre style="white-space:pre-wrap;font-size:13px">R1 LJM/Chewco/Raptor/Whitewing/SPEs
R2 California market trading/prices/caps/ISO
R3 Document retention/destruction
Privileged = lawyer communication for legal advice (footer alone is not)</pre></div>
<script>let docs=[],i=0,cur={};
async function init(){const d=await (await fetch('/api/state')).json();docs=d.docs;window.L=d.labels;i=docs.findIndex(x=>!L[x]);if(i<0)i=0;show()}
function show(){const id=docs[i];cur=Object.assign({responsive:null,request:'none',privileged:false},L[id]||{});
document.getElementById('img').src='/scan/'+id;document.getElementById('t').textContent=id;
document.getElementById('prog').textContent=Object.keys(L).length+' / '+docs.length+' labeled';paint()}
function paint(){br.className=cur.responsive===true?'on':'';bn.className=cur.responsive===false?'on':'';
b1.className=cur.request=='R1'?'on':'';b2.className=cur.request=='R2'?'on':'';b3.className=cur.request=='R3'?'on':'';bp.className=cur.privileged?'on':''}
function set(k,v){cur[k]=v;if(k=='responsive'&&!v)cur.request='none';if(k=='request')cur.responsive=true;paint()}
function toggle(){cur.privileged=!cur.privileged;paint()}
async function save(){if(cur.responsive===null){alert('Pick responsive or not');return}
if(cur.responsive&&cur.request=='none'){alert('Pick a request');return}
await fetch('/api/label/'+docs[i],{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cur)});L[docs[i]]=cur;go(1)}
function go(d){i=Math.max(0,Math.min(docs.length-1,i+d));show()}
document.onkeydown=e=>{const k=e.key;if(k=='r')set('responsive',true);else if(k=='n')set('responsive',false);else if('123'.includes(k)&&k.length==1)set('request','R'+k);else if(k=='p')toggle();else if(k=='Enter')save()};
init()</script>"""

@app.get("/")
def index(): return PAGE

@app.get("/scan/<doc>")
def scan(doc): return send_file(ROOT / "data" / "scans" / f"{doc}.jpg")

@app.get("/api/state")
def state(): return jsonify({"docs": DOCS, "labels": load()})

@app.post("/api/label/<doc>")
def label(doc):
    L = load(); L[doc] = request.get_json(); LABELS.parent.mkdir(exist_ok=True)
    LABELS.write_text(json.dumps(L, indent=1)); return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8800)
