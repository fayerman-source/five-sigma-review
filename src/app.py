"""Live demo: upload any scan, photo or PDF; see each stage and why it was auto-decided or sent to a human."""
import base64, html, io, sys, tempfile, traceback
from pathlib import Path
from flask import Flask, request
from PIL import Image, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
MAX_SIDE = 2200  # phone photos are downscaled to this; text stays readable and uploads stay fast

FORM = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Five Sigma Review</title>
<style>body{font:16px system-ui;max-width:1200px;margin:24px auto;padding:0 16px;color:#111}h1{margin:0 0 4px}
.card{border:1px solid #ddd;border-radius:10px;padding:14px 16px;margin:12px 0}.bar{height:10px;background:#eee;border-radius:5px;overflow:hidden}
.bar i{display:block;height:100%;background:#2a7}.auto{background:#e6f6ec;border-color:#2a7}.human{background:#fff3e0;border-color:#e90}
.err{background:#fdecec;border-color:#c22}pre{white-space:pre-wrap;font-size:13px;max-height:360px;overflow:auto;background:#fafafa;padding:8px}
mark{background:#ffe27a}.ok{color:#2a7;font-weight:600}.bad{color:#c22;font-weight:600}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
img,embed{max-width:100%;width:100%;border:1px solid #ccc}embed{height:720px}button{font-size:16px;padding:6px 14px}
#wait{display:none;margin:12px 0;color:#555}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
<h1>Five Sigma Review</h1><p>First-pass legal review you can check: every call has calibrated confidence and verbatim evidence, or it goes to a human.</p>
<form method=post enctype=multipart/form-data onsubmit="document.getElementById('wait').style.display='block';this.querySelector('button').disabled=true">
<input type=file name=f accept="image/*,application/pdf" required> <button>Review</button></form>
<div id=wait>Reading the page, deciding, finding evidence, checking quotes… about 10 seconds.</div>"""

def bar(p): return f'<div class=bar><i style="width:{p*100:.0f}%"></i></div>{p:.2f}'

def prepare(upload):
    """Save the upload as a PDF or an upright, reasonably sized JPEG. Returns (path, html preview)."""
    raw = upload.read()
    tmp = Path(tempfile.mkdtemp())
    if raw[:5] == b"%PDF-":
        path = tmp / "upload.pdf"; path.write_bytes(raw)
        return path, f'<embed type="application/pdf" src="data:application/pdf;base64,{base64.b64encode(raw).decode()}">'
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")  # phones store rotation in EXIF
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    path = tmp / "upload.jpg"; img.save(path, quality=90)
    return path, f'<img src="data:image/jpeg;base64,{base64.b64encode(path.read_bytes()).decode()}">'

def error_card(msg):
    return FORM + f'<div class="card err"><b>Could not review this file.</b><br>{html.escape(msg)}<br>Nothing was decided. Try again, or use a JPEG, PNG or PDF.</div>'

@app.errorhandler(413)
def too_big(e): return error_card("The file is larger than 25 MB."), 413

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET": return FORM
    try:
        path, preview = prepare(request.files["f"])
    except Exception as e:
        return error_card(f"The file could not be opened as an image or PDF ({type(e).__name__}).")
    try:
        r = P.review(path)
    except Exception as e:
        traceback.print_exc()
        return error_card(f"A model call failed: {str(e)[:200]}")
    text = html.escape(r["transcription"])
    for k, c in r["evidence"].items():
        if c["verified"] and c["quote"]: text = text.replace(html.escape(c["quote"]), f"<mark>{html.escape(c['quote'])}</mark>")
    pr = r["probs"]
    cls = "auto" if r["decision"] == "auto" else "human"
    verdict = ("AUTO-DECIDED" if cls == "auto" else "SENT TO HUMAN REVIEW: " + html.escape("; ".join(r["reasons"])))
    ev = "".join(f'<li><b>{html.escape(k)}</b>: “{html.escape(c["quote"] or "—")}” '
                 f'<span class={"ok" if c["verified"] else "bad"}>{"✓ found on page" if c["verified"] else "✗ not on page"}</span></li>'
                 for k, c in r["evidence"].items()) or "<li>No positive calls, so no evidence needed.</li>"
    return FORM + f"""<div class="card {cls}"><b>{verdict}</b><br>Responsive: <b>{r['responsive']}</b> ({html.escape(str(r['request']))}) · Privileged: <b>{r['privileged']}</b> · {r['seconds']} s · auto-decision threshold {P.THRESH}</div>
<div class=grid><div class=card><b>Uploaded page</b><br>{preview}</div>
<div><div class=card><b>1 · Read</b> (gemini-4-hydrogen)<pre>{text}</pre></div>
<div class=card><b>2 · Decide</b> (Decisions API, calibrated)<br>Responsive {bar(pr['p_responsive'])}<br>Privileged {bar(pr['p_privileged'])}<br>
Request: {", ".join(f"{html.escape(str(k))} {v:.2f}" for k, v in sorted(pr['p_request'].items(), key=lambda x: -x[1]))}
<br><br><b>3 · Evidence</b> (gemini-4-neon) + <b>4 · Code check</b><ul>{ev}</ul></div></div></div>"""

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8801")))
