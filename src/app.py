"""Live demo: upload any scan, photo or PDF; see each stage and why it was auto-decided or sent to a human."""
import json, sys, tempfile, html
from pathlib import Path
from flask import Flask, request
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P

app = Flask(__name__)
FORM = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Five Sigma Review</title>
<style>body{font:16px system-ui;max-width:1100px;margin:24px auto;padding:0 16px;color:#111}h1{margin:0 0 4px}
.card{border:1px solid #ddd;border-radius:10px;padding:14px 16px;margin:12px 0}.bar{height:10px;background:#eee;border-radius:5px;overflow:hidden}
.bar i{display:block;height:100%;background:#2a7}.auto{background:#e6f6ec;border-color:#2a7}.human{background:#fff3e0;border-color:#e90}
pre{white-space:pre-wrap;font-size:13px;max-height:360px;overflow:auto;background:#fafafa;padding:8px}mark{background:#ffe27a}
.ok{color:#2a7;font-weight:600}.bad{color:#c22;font-weight:600}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{max-width:100%;border:1px solid #ccc}</style>
<h1>Five Sigma Review</h1><p>First-pass legal review you can check: every call has calibrated confidence and verbatim evidence, or it goes to a human.</p>
<form method=post enctype=multipart/form-data><input type=file name=f accept="image/*,application/pdf" capture=environment required> <button>Review</button></form>"""

def bar(p): return f'<div class=bar><i style="width:{p*100:.0f}%"></i></div>{p:.2f}'

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET": return FORM
    f = request.files["f"]; suf = Path(f.filename).suffix.lower() or ".jpg"
    tmp = Path(tempfile.mkdtemp()) / ("upload" + (suf if suf in (".jpg", ".jpeg", ".png", ".pdf") else ".jpg"))
    f.save(tmp)
    r = P.review(tmp)
    text = html.escape(r["transcription"])
    for k, c in r["evidence"].items():
        if c["verified"] and c["quote"]: text = text.replace(html.escape(c["quote"]), f"<mark>{html.escape(c['quote'])}</mark>")
    pr = r["probs"]
    cls = "auto" if r["decision"] == "auto" else "human"
    verdict = ("AUTO-DECIDED" if cls == "auto" else "SENT TO HUMAN REVIEW: " + "; ".join(r["reasons"]))
    ev = "".join(f'<li><b>{html.escape(k)}</b>: “{html.escape(c["quote"] or "—")}” '
                 f'<span class={"ok" if c["verified"] else "bad"}>{"✓ found on page" if c["verified"] else "✗ not on page"}</span></li>'
                 for k, c in r["evidence"].items()) or "<li>No positive calls, so no evidence needed.</li>"
    return FORM + f"""<div class="card {cls}"><b>{verdict}</b><br>Responsive: <b>{r['responsive']}</b> ({r['request']}) · Privileged: <b>{r['privileged']}</b> · {r['seconds']} s</div>
<div class=grid><div class=card><b>1 · Read</b> (gemini-4-hydrogen)<pre>{text}</pre></div>
<div class=card><b>2 · Decide</b> (Decisions API, calibrated)<br>Responsive {bar(pr['p_responsive'])}<br>Privileged {bar(pr['p_privileged'])}<br>
Request: {", ".join(f"{k} {v:.2f}" for k, v in sorted(pr['p_request'].items(), key=lambda x: -x[1]))}
<br><br><b>3 · Evidence</b> (gemini-4-neon) + <b>4 · Code check</b><ul>{ev}</ul></div></div>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8801)
