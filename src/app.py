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
.pick{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;gap:12px;align-items:center;cursor:pointer;text-align:left;font:inherit;color:inherit}
.pick:hover,.pick:focus-visible{border-color:var(--ink);outline:none}.pick.sel{border-color:var(--ink);box-shadow:0 0 0 1px var(--ink)}
.pick img{width:64px;height:82px;object-fit:cover;object-position:top;border:1px solid var(--line);border-radius:4px;flex:none}
.pick b{display:block;font-size:17px}.pick span{color:var(--muted);font-size:14px}.pick.up{border-style:dashed;justify-content:center;min-height:108px}
.pick.up.sel{border-style:solid}
.pick[disabled]{opacity:.5;cursor:wait}
#out{display:none}
.own{display:block;margin-top:12px;color:var(--muted);font-size:14px}.own input{display:block;width:100%;margin-top:4px;padding:9px 12px;font:inherit;color:var(--ink);border:1px solid var(--line);border-radius:10px;background:var(--card)}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 12px}.step{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:14px;color:var(--muted)}
.step b{display:block;color:var(--ink);font-size:15px}.step.run{border-color:var(--ink)}.step.run b::after{content:" …"}.step.done b::after{content:" ✓";color:var(--go)}
#verdict{border-radius:14px;padding:18px 22px;border:2px solid var(--line);background:var(--card)}
#verdict.auto{background:var(--gobg);border-color:var(--go)}#verdict.human{background:var(--stopbg);border-color:var(--stop)}#verdict.err{border-color:var(--bad)}
#vtitle{font-size:34px;font-weight:800;letter-spacing:-.02em;line-height:1.1}#verdict.auto #vtitle{color:var(--go)}#verdict.human #vtitle{color:var(--stop)}#verdict.err #vtitle{color:var(--bad)}
#vwhy{font-size:18px;margin-top:6px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;min-height:118px}
.tile h3{margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}.big{font-size:28px;font-weight:800;line-height:1.15;margin-top:4px}
.sub{color:var(--muted);font-size:14px}.bar{height:8px;background:#e8ebf0;border-radius:4px;overflow:hidden;margin:8px 0 4px}.bar i{display:block;height:100%;background:var(--ink);width:0;transition:width .5s}
.quote{font-size:15px;margin-top:6px}.quote q{background:var(--mark);padding:1px 3px}.ok{color:var(--go);font-weight:700}.no{color:var(--bad);font-weight:700}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.panel h3{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
.pnote{background:var(--stopbg);color:var(--stop);border:1px solid var(--stop);border-radius:8px;padding:6px 10px;font-size:13px;font-weight:600;margin-bottom:8px}
.panel img,.panel embed{width:100%;border:1px solid var(--line);border-radius:4px}.panel embed{height:640px}
pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Consolas,monospace;margin:0;max-height:640px;overflow:auto}mark{background:var(--mark);padding:1px 0}
.wait{color:var(--muted)}footer{margin-top:22px;color:var(--muted);font-size:13px}
@media(max-width:820px){.tiles,.cols{grid-template-columns:1fr}#vtitle{font-size:26px}}
</style>
<main>
<h1>Five Sigma Review</h1>
<p class=tag>First-pass legal document review that proves each call with a quote from the page, or hands the page to a human.</p>
<div class=start id=start>__SAMPLES__
<button class="pick up" id=upbtn><span><b>Upload your own</b>scan, phone photo or PDF</span></button>
<input type=file id=file accept="image/*,application/pdf" hidden>
</div>
<label class=own>Looking for something else? Type your own request and it replaces the three built-in ones (optional)<input id=custom maxlength=300 placeholder="for example: documents about pricing or discounts" autocomplete=off></label>
<div class=steps>
<div class=step id=s1><b>1 · Read</b>Gemini 4 Hydrogen transcribes the page</div>
<div class=step id=s2><b>2 · Decide</b>Decisions API gives probabilities</div>
<div class=step id=s3><b>3 · Evidence</b>Gemini 4 Neon finds the quote</div>
<div class=step id=s4><b>4 · Check</b>Code verifies the quote is on the page</div>
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
<footer>Built-in requests: R1 partnerships and off-balance-sheet vehicles (LJM, Raptor, Chewco, Whitewing) · R2 California electricity market · R3 document retention or destruction. A page is decided automatically only if confidence is at least __THRESH__ and every quote is found verbatim; otherwise a human gets it. Public data only. Not legal advice.</footer>
</main>
<script>
const $=id=>document.getElementById(id), REQ0={R1:"R1 · partnerships / off-balance-sheet",R2:"R2 · California power market",R3:"R3 · document retention",none:"no request"};let REQ=REQ0,hasCustom=false;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let busy=false,timer=null,t0=0,rawText="";
function selectCard(el){document.querySelectorAll(".pick").forEach(b=>b.classList.toggle("sel",b===el))}
function step(n,state){for(let i=1;i<=4;i++){const e=$("s"+i);e.className="step"+(i<n?" done":i===n?" "+state:"")}}
function reset(){$("out").style.display="block";$("verdict").className="";$("vtitle").textContent="Working…";$("vwhy").textContent="";$("vwhy").className="wait";
 for(const k of["rbig","pbig"])$(k).textContent="–";for(const k of["rsub","psub"])$(k).textContent="";$("rbar").style.width=$("pbar").style.width="0";
 $("proof").innerHTML="–";$("pnote").hidden=true;$("pnote").textContent="";$("page").innerHTML="…";$("text").textContent="…";$("text").className="wait";rawText="";step(1,"run");
 t0=Date.now();clearInterval(timer);timer=setInterval(()=>{if(busy)$("vwhy").textContent=((Date.now()-t0)/1000).toFixed(0)+" s"},250);
 $("s1").scrollIntoView({behavior:"smooth",block:"start"})}
function highlight(quotes){let h=esc(rawText);
 for(const q of quotes){const words=q.trim().split(/\s+/).map(w=>esc(w).replace(/[.*+?^${}()|[\]\\]/g,"\\$&"));
  try{h=h.replace(new RegExp(words.join("\\s+"),"i"),m=>"<mark>"+m+"</mark>")}catch(e){}}
 $("text").innerHTML=h;const m=$("text").querySelector("mark");if(m)$("text").scrollTop=Math.max(0,m.offsetTop-$("text").offsetTop-80)}
function on(ev){
 if(ev.stage==="page"){hasCustom=Boolean(ev.custom);REQ=ev.custom?{R1:"your request: "+ev.custom,none:"no request"}:REQ0;
  if(ev.pages&&ev.pages>1){$("pnote").textContent="Preview shows page 1 of "+ev.pages+". The whole PDF was sent to the models.";$("pnote").hidden=false}
  $("page").className="";$("page").innerHTML=ev.kind==="pdf"?`<embed type="application/pdf" src="${ev.src}">`:`<img alt="uploaded page" src="${ev.src}">`}
 else if(ev.stage==="read"){rawText=ev.text;$("text").className="";$("text").textContent=ev.text;step(2,"run")}
 else if(ev.stage==="decide"){const p=ev.probs,r=p.p_responsive,v=p.p_privileged;
  $("rbig").textContent=r>=.5?"Yes":"No";$("rbar").style.width=(Math.max(r,1-r)*100)+"%";$("rsub").textContent=Math.round(Math.max(r,1-r)*100)+"% confident"+(r>=.5?" · "+(REQ[p.request]||p.request):"");
  $("pbig").textContent=v>=.5?"Yes":"No";$("pbar").style.width=(Math.max(v,1-v)*100)+"%";$("psub").textContent=Math.round(Math.max(v,1-v)*100)+"% confident";step(3,"run")}
 else if(ev.stage==="evidence"){step(4,"run")}
 else if(ev.stage==="final"){const r=ev.result,items=Object.entries(r.evidence);
  $("proof").innerHTML=items.length?items.map(([k,c])=>{const label=hasCustom&&k==="responsive to R1"?"responsive to your request":k;return `<div class=quote><b>${esc(label)}</b><br>${c.quote?"<q>"+esc(c.quote)+"</q>":"no quote offered"}<br><span class="${c.verified?"ok":"no"}">${c.verified?"✓ found word for word on the page":"✗ not on the page"}</span></div>`}).join(""):"No positive call was made, so there is nothing to prove.";
  highlight(items.filter(([k,c])=>c.verified&&c.quote).map(([k,c])=>c.quote));for(let i=1;i<=4;i++)$("s"+i).className="step done";
  const auto=r.decision==="auto";$("verdict").className=auto?"auto":"human";$("vtitle").textContent=auto?"Decided automatically":"Sent to a human";
  const call=(r.responsive?"Responsive ("+(REQ[r.request]||r.request)+")":"Not responsive")+", "+(r.privileged?"privileged":"not privileged");
  const qmsg=items.length?"every quote verified":"no positive call, so no quote was needed";
  $("vwhy").className="";$("vwhy").textContent=auto?call+". Confidence "+Math.round(r.confidence*100)+"%, "+qmsg+". "+r.seconds+" s.":"Why: "+r.reasons.join("; ")+". The system's tentative call was: "+call+". "+r.seconds+" s."}
 else if(ev.stage==="error"){$("verdict").className="err";$("vtitle").textContent="Could not review this file";$("vwhy").className="";$("vwhy").textContent=ev.message+" Nothing was decided."}}
async function run(body){if(busy)return;busy=true;document.querySelectorAll(".pick").forEach(b=>b.disabled=true);reset();
 try{const res=await fetch("/api/review",{method:"POST",body});if(!res.ok&&res.status===413){on({stage:"error",message:"The file is larger than 25 MB."});return}
  const rd=res.body.getReader(),dec=new TextDecoder();let buf="";
  for(;;){const{done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});let i;
   while((i=buf.indexOf("\n"))>=0){const line=buf.slice(0,i).trim();buf=buf.slice(i+1);if(line)on(JSON.parse(line))}}}
 catch(e){on({stage:"error",message:"The connection to the demo server failed ("+e.message+")."})}
 finally{busy=false;clearInterval(timer);document.querySelectorAll(".pick").forEach(b=>b.disabled=false)}}
document.querySelectorAll("[data-sample]").forEach(b=>b.onclick=()=>{if(busy)return;selectCard(b);const f=new FormData();f.append("sample",b.dataset.sample);f.append("custom",$("custom").value);run(f)});
$("upbtn").onclick=()=>$("file").click();
$("file").onchange=e=>{if(e.target.files[0]&&!busy){selectCard($("upbtn"));const f=new FormData();f.append("f",e.target.files[0]);f.append("custom",$("custom").value);run(f);e.target.value=""}};
</script></html>"""

def page_html():
    cards = "".join(f'<button class=pick data-sample="{s["id"]}"><img alt="" src="/sample/{s["id"]}"><span><b>{s["title"]}</b>{s["note"]}</span></button>' for s in SAMPLES)
    return PAGE.replace("__SAMPLES__", cards).replace("__THRESH__", str(P.THRESH))

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
    return max(1, len(re.findall(r"/Type\s*/Page\b", raw_txt)))

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
        t0 = time.time()
        text = P.read_page(path); yield line(stage="read", text=text)
        dec = P.decide(path, text, custom); yield line(stage="decide", probs=dec)
        ev = P.evidence(text, dec, custom); yield line(stage="evidence")
        yield line(stage="final", result=P.finalize(text, dec, ev, t0))
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
