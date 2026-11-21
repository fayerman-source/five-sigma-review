"""Live demo: pick a sample or upload any scan, photo or PDF; each stage appears as it finishes,
then a verdict: decided automatically (with the verified quote) or sent to a human (with the reason)."""
import base64, io, json, os, re, subprocess, sys, tempfile, time, traceback
from pathlib import Path
from flask import Flask, Response, request, send_file, stream_with_context, abort
from PIL import Image, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P

ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT / "data" / "samples"
SAMPLES = json.loads((SAMPLES_DIR / "samples.json").read_text()) if (SAMPLES_DIR / "samples.json").exists() else []
MAX_SIDE = 2200  # phone photos are downscaled to this; text stays readable and uploads stay fast
DEFAULT_THRESH = 0.80  # operating point picked on tuning set in sweep.py (0.90 was pre-registered)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

PAGE = r"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Five Sigma Review</title>
<style>
:root{--ink:#14181f;--muted:#5b6472;--line:#dfe3ea;--bg:#f6f7f9;--card:#fff;--go:#0f7b4a;--gobg:#e3f4ea;--stop:#b45309;--stopbg:#fdf0dc;--bad:#b42318;--mark:#ffe27a}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg)}
main{max-width:1240px;margin:0 auto;padding:20px 20px 60px}
h1{font-size:30px;margin:0;letter-spacing:-.02em}.tag{font-size:18px;color:var(--muted);margin:4px 0 18px}
.start{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.pick{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;gap:12px;align-items:center;cursor:pointer;text-align:left;font:inherit;color:inherit;transition:border-color .15s,background .15s}
.pick:hover,.pick:focus-visible{border-color:var(--ink);outline:none}.pick img{width:64px;height:82px;object-fit:cover;object-position:top;border:1px solid var(--line);border-radius:4px;flex:none}
.pick b{display:block;font-size:17px}.pick span{color:var(--muted);font-size:14px}.pick.up{border-style:dashed;justify-content:center;min-height:108px;text-align:center}
.pick.up.drag{border-color:var(--go);border-style:solid;background:var(--gobg)}
.pick[disabled]{opacity:.5;cursor:wait}
#out{display:none}
.own{display:block;margin-top:12px;color:var(--muted);font-size:14px}.own input{display:block;width:100%;margin-top:4px;padding:9px 12px;font:inherit;color:var(--ink);border:1px solid var(--line);border-radius:10px;background:var(--card)}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 12px}.step{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:14px;color:var(--muted)}
.step b{display:flex;justify-content:space-between;align-items:baseline;gap:6px;color:var(--ink);font-size:15px}
.st{font-weight:600;font-size:13px;color:var(--muted)}.step.run{border-color:var(--ink)}.step.run .st::after{content:"…"}.step.done .st{color:var(--go)}
.tbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;margin:0 0 12px;font-size:14px;color:var(--muted)}
.tbar label{font-weight:600;color:var(--ink)}.tbar input[type=range]{flex:1;min-width:160px;accent-color:var(--ink);cursor:pointer}
.tval{font-variant-numeric:tabular-nums;font-weight:700;color:var(--ink);min-width:170px}
.tpill{border:1px solid var(--line);background:var(--bg);color:var(--muted);border-radius:999px;padding:3px 10px;font:12px/1.3 inherit;cursor:pointer}
.tpill:hover,.tpill.on{border-color:var(--ink);color:var(--ink);background:var(--card);font-weight:600}
#verdict{border-radius:14px;padding:18px 22px;border:2px solid var(--line);background:var(--card)}
#verdict.auto{background:var(--gobg);border-color:var(--go)}#verdict.human{background:var(--stopbg);border-color:var(--stop)}#verdict.err{border-color:var(--bad)}
#vtitle{font-size:34px;font-weight:800;letter-spacing:-.02em;line-height:1.1}#verdict.auto #vtitle{color:var(--go)}#verdict.human #vtitle{color:var(--stop)}#verdict.err #vtitle{color:var(--bad)}
#vwhy{font-size:18px;margin-top:6px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-height:118px}
.tile h3{margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}.big{font-size:28px;font-weight:800;line-height:1.15;margin-top:4px}
.sub{color:var(--muted);font-size:14px}.bar{height:8px;background:#e8ebf0;border-radius:4px;overflow:hidden;margin:8px 0 4px}.bar i{display:block;height:100%;background:var(--ink);width:0;transition:width .5s}
.quote{font-size:15px;margin-top:6px}.quote q{background:var(--mark);padding:1px 3px;border-radius:2px}
.quote.jump{cursor:pointer;border-radius:6px;padding:3px 5px;margin:4px -5px 0;transition:background .15s}.quote.jump:hover{background:#f1f3f7}
.ok{color:var(--go);font-weight:700}.no{color:var(--bad);font-weight:700}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.panel h3{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
.pnote{background:var(--stopbg);color:var(--stop);border:1px solid var(--stop);border-radius:8px;padding:6px 10px;font-size:13px;font-weight:600;margin-bottom:8px}
.panel img,.panel embed{width:100%;border:1px solid var(--line);border-radius:4px}.panel embed{height:640px}
pre{position:relative;white-space:pre-wrap;font:13px/1.5 ui-monospace,Consolas,monospace;margin:0;max-height:640px;overflow:auto}
mark{background:var(--mark);padding:1px 2px;border-radius:2px}
@keyframes markpulse{0%{box-shadow:0 0 0 0 rgba(180,83,9,.85);background:#ffd23f}60%{box-shadow:0 0 0 7px rgba(180,83,9,0);background:#ffd23f}100%{box-shadow:0 0 0 0 rgba(180,83,9,0);background:var(--mark)}}
mark.pulse{animation:markpulse 1.1s ease-out}
.wait{color:var(--muted)}footer{margin-top:22px;color:var(--muted);font-size:13px}
@media(max-width:820px){.tiles,.cols{grid-template-columns:1fr}#vtitle{font-size:26px}}
</style>
<main>
<h1>Five Sigma Review</h1>
<p class=tag>First-pass legal document review that proves each call with a quote from the page, or hands the page to a human.</p>
<div class=start id=start>__SAMPLES__
<button class="pick up" id=upbtn><span><b>Upload your own</b>scan, phone photo or PDF · click, drop or paste</span></button>
<input type=file id=file accept="image/*,application/pdf" hidden>
</div>
<label class=own>Looking for something else? Type your own request and it replaces the three built-in ones (optional)<input id=custom maxlength=300 placeholder="for example: documents about pricing or discounts" autocomplete=off></label>
<div class=steps>
<div class=step id=s1><b><span>1 · Read</span><span class=st id=st1></span></b>Gemini 4 Hydrogen transcribes the page</div>
<div class=step id=s2><b><span>2 · Decide</span><span class=st id=st2></span></b>Decisions API gives probabilities</div>
<div class=step id=s3><b><span>3 · Evidence</span><span class=st id=st3></span></b>Gemini 4 Neon finds the quote</div>
<div class=step id=s4><b><span>4 · Check</span><span class=st id=st4></span></b>Code verifies the quote is on the page</div>
</div>
<div class=tbar>
<label for=thresh>Auto-decision confidence threshold</label>
<input type=range id=thresh min=0.50 max=0.99 step=0.01 value="__DEFAULT_THRESH__">
<span class=tval id=tval></span>
<button type=button class=tpill data-th="0.80">0.80 · picked on tune set</button>
<button type=button class=tpill data-th="0.90">0.90 · pre-registered</button>
</div>
<section id=out aria-live=polite>
<div id=verdict><div id=vtitle>Working…</div><div id=vwhy class=wait></div></div>
<div class=tiles>
<div class=tile><h3>Responsive to a request?</h3><div class=big id=rbig>–</div><div class=bar><i id=rbar></i></div><div class=sub id=rsub></div></div>
<div class=tile><h3>Privileged?</h3><div class=big id=pbig>–</div><div class=bar><i id=pbar></i></div><div class=sub id=psub></div></div>
<div class=tile><h3>Proof from the page</h3><div id=proof class=sub>–</div></div>
</div>
<div class=cols>
<div class=panel><h3>The page</h3><div id=pnote class=pnote hidden></div><div id=page class=wait>…</div></div>
<div class=panel><h3>What the model read</h3><pre id=text class=wait>…</pre></div>
</div>
</section>
<footer>Built-in requests: R1 partnerships and off-balance-sheet vehicles (LJM, Raptor, Chewco, Whitewing) · R2 California electricity market · R3 document retention or destruction. A page is decided automatically only if confidence is at least <span id=fthresh>__DEFAULT_THRESH__</span> and every quote is found verbatim; otherwise a human gets it. Public data only. Not legal advice.</footer>
</main>
<script>
const $=id=>document.getElementById(id), REQ0={R1:"R1 · partnerships / off-balance-sheet",R2:"R2 · California power market",R3:"R3 · document retention",none:"no request"};let REQ=REQ0;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const escRe=s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
let busy=false,timer=null,t0=0,rawText="",lastResult=null;

function step(n,state){for(let i=1;i<=4;i++){const e=$("s"+i);e.className="step"+(i<n?" done":i===n?" "+state:"")}}
function fmtSec(v){return v<0.05?"<0.1s":v.toFixed(1)+"s"}

function syncThreshUI(){
 const th=parseFloat($("thresh").value),s=th.toFixed(2);
 const tag=s==="0.80"?" (picked on tune set)":s==="0.90"?" (pre-registered)":"";
 $("tval").textContent=s+tag;$("fthresh").textContent=s;
 document.querySelectorAll(".tpill").forEach(b=>b.classList.toggle("on",b.dataset.th===s));
 if(lastResult)renderVerdict();
}

function renderVerdict(){
 const r=lastResult;if(!r)return;
 const th=parseFloat($("thresh").value),p=r.probs;
 const conf=p?Math.min(Math.max(p.p_responsive,1-p.p_responsive),Math.max(p.p_privileged,1-p.p_privileged)):r.confidence;
 const reasons=[];
 if(conf<th)reasons.push("low confidence ("+conf.toFixed(2)+" < "+th.toFixed(2)+")");
 for(const[k,c]of Object.entries(r.evidence||{})){if(!c.verified)reasons.push("evidence for '"+k+"' not found verbatim on the page")}
 const auto=reasons.length===0;
 $("verdict").className=auto?"auto":"human";
 $("vtitle").textContent=auto?"Decided automatically":"Sent to a human";
 const call=(r.responsive?"Responsive ("+(REQ[r.request]||r.request)+")":"Not responsive")+", "+(r.privileged?"privileged":"not privileged");
 $("vwhy").className="";
 $("vwhy").textContent=auto?call+". Confidence "+Math.round(conf*100)+"%, every quote verified. "+r.seconds+" s.":"Why: "+reasons.join("; ")+". The system's tentative call was: "+call+". "+r.seconds+" s.";
}

function reset(){
 lastResult=null;$("out").style.display="block";$("verdict").className="";$("vtitle").textContent="Working…";$("vwhy").textContent="";$("vwhy").className="wait";
 for(const k of["rbig","pbig"])$(k).textContent="–";for(const k of["rsub","psub"])$(k).textContent="";$("rbar").style.width=$("pbar").style.width="0";
 for(let i=1;i<=4;i++)$("st"+i).textContent="";
 $("proof").innerHTML="–";$("pnote").hidden=true;$("pnote").textContent="";$("page").innerHTML="…";$("text").textContent="…";$("text").className="wait";rawText="";step(1,"run");
 t0=Date.now();clearInterval(timer);timer=setInterval(()=>{if(busy)$("vwhy").textContent=((Date.now()-t0)/1000).toFixed(0)+" s"},250);
 $("s1").scrollIntoView({behavior:"smooth",block:"start"});
}

function findQuoteSpan(text,q){
 if(!q||!q.trim())return null;
 const words=q.trim().split(/\s+/).map(escRe);
 try{const m=new RegExp(words.join("\\s+"),"i").exec(text);if(m)return[m.index,m.index+m[0].length]}catch(e){}
 const alnum=q.match(/[a-z0-9]+/gi);
 if(alnum&&alnum.length>=3){
  try{const m=new RegExp(alnum.map(escRe).join("[^a-z0-9]+"),"i").exec(text);if(m)return[m.index,m.index+m[0].length]}catch(e){}
 }
 return null;
}

function highlight(quotes){
 const spans=[];
 for(let i=0;i<quotes.length;i++){
  const sp=findQuoteSpan(rawText,quotes[i]);
  if(sp)spans.push({start:sp[0],end:sp[1],idx:i});
 }
 spans.sort((a,b)=>a.start-b.start);
 let out="",pos=0;
 for(const sp of spans){
  if(sp.start<pos)continue;
  out+=esc(rawText.slice(pos,sp.start))+'<mark id="mark-'+sp.idx+'">'+esc(rawText.slice(sp.start,sp.end))+"</mark>";
  pos=sp.end;
 }
 out+=esc(rawText.slice(pos));
 $("text").innerHTML=out;
 const m=$("text").querySelector("mark");
 if(m)$("text").scrollTop=Math.max(0,m.offsetTop-80);
}

function jumpQuote(idx){
 const pre=$("text"),m=$("mark-"+idx)||pre.querySelector("mark");
 if(!m)return;
 const top=pre.scrollTop+m.getBoundingClientRect().top-pre.getBoundingClientRect().top-80;
 pre.scrollTo({top:Math.max(0,top),behavior:"smooth"});
 m.classList.remove("pulse");void m.offsetWidth;m.classList.add("pulse");
}

function on(ev){
 if(ev.stage==="page"){
  REQ=ev.custom?{R1:"your request: "+ev.custom,none:"no request"}:REQ0;
  if(ev.pages&&ev.pages>1){$("pnote").textContent="Page 1 of "+ev.pages+" shown and reviewed (demo is single-page)";$("pnote").hidden=false}
  $("page").className="";$("page").innerHTML=ev.kind==="pdf"?`<embed type="application/pdf" src="${ev.src}">`:`<img alt="uploaded page" src="${ev.src}">`;
 }
 else if(ev.stage==="read"){
  if(typeof ev.elapsed==="number")$("st1").textContent="✓ "+fmtSec(ev.elapsed);
  rawText=ev.text;$("text").className="";$("text").textContent=ev.text;step(2,"run");
 }
 else if(ev.stage==="decide"){
  if(typeof ev.elapsed==="number")$("st2").textContent="✓ "+fmtSec(ev.elapsed);
  const p=ev.probs,r=p.p_responsive,v=p.p_privileged;
  $("rbig").textContent=r>=.5?"Yes":"No";$("rbar").style.width=(Math.max(r,1-r)*100)+"%";$("rsub").textContent=Math.round(Math.max(r,1-r)*100)+"% confident"+(r>=.5?" · "+(REQ[p.request]||p.request):"");
  $("pbig").textContent=v>=.5?"Yes":"No";$("pbar").style.width=(Math.max(v,1-v)*100)+"%";$("psub").textContent=Math.round(Math.max(v,1-v)*100)+"% confident";step(3,"run");
 }
 else if(ev.stage==="evidence"){
  if(typeof ev.elapsed==="number")$("st3").textContent="✓ "+fmtSec(ev.elapsed);
  step(4,"run");
 }
 else if(ev.stage==="final"){
  if(typeof ev.elapsed==="number")$("st4").textContent="✓ "+fmtSec(ev.elapsed);
  const r=ev.result,items=Object.entries(r.evidence||{});
  const vQuotes=[];
  $("proof").innerHTML=items.length?items.map(([k,c])=>{
   let qIdx=-1;
   if(c.verified&&c.quote){qIdx=vQuotes.length;vQuotes.push(c.quote)}
   const cls=qIdx>=0?"quote jump":"quote";
   const attr=qIdx>=0?` data-qidx="${qIdx}" role="button" tabindex="0" title="Jump to quote in transcription"`:"";
   return `<div class="${cls}"${attr}><b>${esc(k)}</b><br>${c.quote?"<q>"+esc(c.quote)+"</q>":"no quote offered"}<br><span class="${c.verified?"ok":"no"}">${c.verified?"✓ found word for word on the page (click to locate)":"✗ not on the page"}</span></div>`;
  }).join(""):"No positive call was made, so there is nothing to prove.";
  $("proof").querySelectorAll("[data-qidx]").forEach(el=>{
   const idx=parseInt(el.dataset.qidx,10);
   el.onclick=()=>jumpQuote(idx);
   el.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();jumpQuote(idx)}};
  });
  highlight(vQuotes);
  for(let i=1;i<=4;i++)$("s"+i).className="step done";
  lastResult=r;renderVerdict();
 }
 else if(ev.stage==="error"){$("verdict").className="err";$("vtitle").textContent="Could not review this file";$("vwhy").className="";$("vwhy").textContent=ev.message+" Nothing was decided."}
}

async function run(body){
 if(busy)return;busy=true;document.querySelectorAll(".pick").forEach(b=>b.disabled=true);reset();
 try{
  const res=await fetch("/api/review",{method:"POST",body});
  if(!res.ok&&res.status===413){on({stage:"error",message:"The file is larger than 25 MB."});return}
  const rd=res.body.getReader(),dec=new TextDecoder();let buf="";
  for(;;){const{done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});let i;
   while((i=buf.indexOf("\n"))>=0){const line=buf.slice(0,i).trim();buf=buf.slice(i+1);if(line)on(JSON.parse(line))}}
 }
 catch(e){on({stage:"error",message:"The connection to the demo server failed ("+e.message+")."})}
 finally{busy=false;clearInterval(timer);document.querySelectorAll(".pick").forEach(b=>b.disabled=false)}
}

function submitFile(file){
 if(!file||busy)return;
 const f=new FormData();f.append("f",file);f.append("custom",$("custom").value);run(f);
}

$("thresh").oninput=syncThreshUI;
document.querySelectorAll(".tpill").forEach(b=>b.onclick=()=>{$("thresh").value=b.dataset.th;syncThreshUI()});
syncThreshUI();

document.querySelectorAll("[data-sample]").forEach(b=>b.onclick=()=>{const f=new FormData();f.append("sample",b.dataset.sample);f.append("custom",$("custom").value);run(f)});
$("upbtn").onclick=()=>$("file").click();
$("file").onchange=e=>{if(e.target.files[0]){submitFile(e.target.files[0]);e.target.value=""}};

["dragenter","dragover"].forEach(ev=>$("upbtn").addEventListener(ev,e=>{e.preventDefault();e.stopPropagation();if(!busy)$("upbtn").classList.add("drag")}));
$("upbtn").addEventListener("dragleave",e=>{e.preventDefault();if(!$("upbtn").contains(e.relatedTarget))$("upbtn").classList.remove("drag")});
$("upbtn").addEventListener("drop",e=>{e.preventDefault();e.stopPropagation();$("upbtn").classList.remove("drag");const file=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];if(file)submitFile(file)});
window.addEventListener("dragover",e=>e.preventDefault());
window.addEventListener("drop",e=>e.preventDefault());

document.addEventListener("paste",e=>{
 const items=e.clipboardData&&e.clipboardData.items?[...e.clipboardData.items]:[];
 const it=items.find(x=>x.kind==="file"&&(x.type.startsWith("image/")||x.type==="application/pdf"));
 const file=it?it.getAsFile():(e.clipboardData&&e.clipboardData.files&&e.clipboardData.files[0]);
 if(file){e.preventDefault();submitFile(file)}
});
</script></html>"""

def page_html():
    cards = "".join(f'<button class=pick data-sample="{s["id"]}"><img alt="" src="/sample/{s["id"]}"><span><b>{s["title"]}</b>{s["note"]}</span></button>' for s in SAMPLES)
    return PAGE.replace("__SAMPLES__", cards).replace("__DEFAULT_THRESH__", f"{DEFAULT_THRESH:.2f}")

def pdf_page_count(path):
    """Count pages in a PDF via pdfinfo, falling back to regex page count."""
    try:
        r = subprocess.run(["/usr/bin/pdfinfo", str(path)], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
            if m: return max(1, int(m.group(1)))
    except FileNotFoundError:
        pass
    raw_txt = Path(path).read_bytes().decode("latin-1", errors="ignore")
    n = len(re.findall(r"/Type\s*/Page\b", raw_txt))
    return max(1, n)

def prepare(raw):
    """Save bytes as a PDF or an upright, reasonably sized JPEG. Returns (path, kind, data URI for preview, pages)."""
    tmp = Path(tempfile.mkdtemp())
    if raw[:5] == b"%PDF-":
        path = tmp / "upload.pdf"; path.write_bytes(raw)
        pages = pdf_page_count(path)
        preview_prefix = tmp / "preview"
        try:
            subprocess.run(["/usr/bin/pdftoppm", "-f", "1", "-l", "1", "-r", "150", "-jpeg", "-singlefile", str(path), str(preview_prefix)],
                           capture_output=True, timeout=30, check=True)
        except FileNotFoundError:
            return path, "pdf", "data:application/pdf;base64," + base64.b64encode(raw).decode(), pages
        except subprocess.CalledProcessError as e:
            raise ValueError("unreadable PDF") from e
        jpg = tmp / "preview.jpg"
        if not jpg.exists() or jpg.stat().st_size == 0:
            raise ValueError("empty PDF preview")
        return path, "image", "data:image/jpeg;base64," + base64.b64encode(jpg.read_bytes()).decode(), pages
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")  # phones store rotation in EXIF
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    path = tmp / "upload.jpg"; img.save(path, quality=90)
    return path, "image", "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode(), 1

def stages(path, kind, src, custom=None, pages=1):
    """Run the pipeline one stage at a time, yielding one JSON line per finished stage."""
    def line(**k): return json.dumps(k) + "\n"
    yield line(stage="page", kind=kind, src=src, custom=custom, pages=pages)
    try:
        t0 = time.time(); ts = t0
        text = P.read_page(path); now = time.time(); yield line(stage="read", text=text, elapsed=round(now - ts, 1)); ts = now
        dec = P.decide(path, text, custom); now = time.time(); yield line(stage="decide", probs=dec, elapsed=round(now - ts, 1)); ts = now
        ev = P.evidence(text, dec, custom); now = time.time(); yield line(stage="evidence", elapsed=round(now - ts, 1)); ts = now
        res = P.finalize(text, dec, ev, t0); now = time.time(); yield line(stage="final", result=res, elapsed=round(now - ts, 1))
    except Exception as e:
        traceback.print_exc()
        yield line(stage="error", message=f"A model call failed: {str(e)[:200]}")

def ndjson(gen): return Response(stream_with_context(gen), mimetype="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})

@app.get("/")
def index(): return page_html()

@app.get("/sample/<sid>")
def sample(sid):
    s = next((s for s in SAMPLES if s["id"] == sid), None)
    if not s: abort(404)
    return send_file(SAMPLES_DIR / s["file"])

@app.errorhandler(413)
def too_big(e): return "too large", 413

@app.post("/api/review")
def api_review():
    try:
        sid = request.form.get("sample")
        if sid:
            s = next(s for s in SAMPLES if s["id"] == sid)
            raw = (SAMPLES_DIR / s["file"]).read_bytes()
        else:
            raw = request.files["f"].read()
        path, kind, src, pages = prepare(raw)
    except Exception as e:
        return ndjson(iter([json.dumps({"stage": "error", "message": f"The file could not be opened as an image or PDF ({type(e).__name__})."}) + "\n"]))
    custom = (request.form.get("custom") or "").strip()[:300] or None
    return ndjson(stages(path, kind, src, custom, pages))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8801")), threaded=True)
