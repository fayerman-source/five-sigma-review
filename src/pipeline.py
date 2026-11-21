"""5 Sigma document review: three Gemini 4 stages + code checks, fail-closed.

1. READ    gemini-4-hydrogen  scanned page image -> faithful transcription (numbered lines)
2. DECIDE  gemini-decision-1  calibrated probabilities on the IMAGE + transcription:
                              responsive (yes/no), which request (R1/R2/R3/none), privileged (yes/no)
3. EVIDENCE gemini-4-neon     for each positive call, the exact sentence(s) that support it
4. CODE    verify every quote appears verbatim in the transcription; auto-decide only when
           confidence >= threshold AND evidence verifies; otherwise route to a human.
Baseline: one gemini-4-hydrogen call on the image that answers everything at once."""
import base64, json, os, re, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://generativelanguage.googleapis.com/v1beta"
REQUESTS = (ROOT / "data" / "requests.md").read_text()
READER, EVIDENCE, BASELINE = "gemini-4-hydrogen", "gemini-4-neon", "gemini-4-hydrogen"
THRESH = float(os.environ.get("AUTO_THRESHOLD", "0.9"))

def _key():
    """Key lookup order: GEMINI_API_KEY in the environment, then .env.hackathon, then .env (both gitignored)."""
    k = os.environ.get("GEMINI_API_KEY")
    for name in (".env.hackathon", ".env"):
        f = ROOT / name
        if k or not f.exists(): continue
        for line in f.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="): k = line.split("=", 1)[1].strip().strip('"\'')
    return k

def _post(path, body, tries=4):
    data = json.dumps(body).encode()
    for i in range(tries):
        req = urllib.request.Request(f"{API}/{path}", data=data, headers={"x-goog-api-key": _key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (429, 500, 503) and i < tries - 1: time.sleep(4 * (i + 1)); continue
            raise RuntimeError(f"{e.code}: {msg}")
        except Exception:
            if i < tries - 1: time.sleep(3); continue
            raise

def _img_part(path):
    b = Path(path).read_bytes()
    mime = "application/pdf" if str(path).lower().endswith(".pdf") else ("image/png" if str(path).lower().endswith(".png") else "image/jpeg")
    return mime, base64.b64encode(b).decode()

def _gen(model, parts, json_mode=False, thinking="low"):
    cfg = {"thinkingConfig": {"thinkingLevel": thinking}}
    if json_mode: cfg["responseMimeType"] = "application/json"
    d = _post(f"models/{model}:generateContent", {"contents": [{"role": "user", "parts": parts}], "generationConfig": cfg})
    parts = d["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))

def read_page(path):
    mime, data = _img_part(path)
    t = _gen(READER, [{"inline_data": {"mime_type": mime, "data": data}},
        {"text": "Transcribe this scanned document page exactly as written, line by line, keeping spelling, "
                 "punctuation and line breaks. Include headers, stamps and any handwritten notes (prefix those with "
                 "[handwritten]). Do not summarize, correct or add anything. Output only the transcription."}])
    return t.strip()

def decide(path, text):
    mime, data = _img_part(path)
    kind = "document" if mime == "application/pdf" else "image"
    body = {"model": "gemini-decision-1",
            "input": [{"role": "user", "parts": [{kind: {"data": data, "mime_type": mime}},
                      {"text": "Review instructions:\n" + REQUESTS + "\n\nTranscription of the page:\n" + text}]}],
            "questions": {
                "responsive": {"type": "noul", "instructions": "Under the review instructions, is this document RESPONSIVE to at least one request (R1, R2 or R3)?"},
                "request": {"type": "choice", "instructions": "Which request does this document most concern?",
                            "criteria": {"R1": "Partnerships / off-balance-sheet vehicles (LJM, Chewco, Raptor, Whitewing)",
                                         "R2": "California electricity market trading, prices, caps, ISO/PX",
                                         "R3": "Document retention, preservation or destruction",
                                         "none": "None of the requests"}},
                "privileged": {"type": "noul", "instructions": "Under the review instructions, is this document PRIVILEGED (a confidential lawyer communication seeking or giving legal advice)? A confidentiality footer alone is not enough."}}}
    try:
        d = _post("decisions", body)
    except RuntimeError as e:
        if "input" not in str(e): raise
        body["input"] = "Review instructions:\n" + REQUESTS + "\n\nTranscription of the page:\n" + text
        d = _post("decisions", body)
    a = d["answers"]
    return {"p_responsive": a["responsive"]["noul"], "request": a["request"]["choice"],
            "p_request": a["request"].get("probabilities", {}), "p_privileged": a["privileged"]["noul"]}

def evidence(text, dec):
    want = []
    if dec["p_responsive"] >= 0.5: want.append(f"responsive to {dec['request']}")
    if dec["p_privileged"] >= 0.5: want.append("privileged")
    if not want: return {}
    t = _gen(EVIDENCE, [{"text": "Review instructions:\n" + REQUESTS + "\n\nDocument transcription:\n" + text +
        "\n\nFor each call below, copy the shortest exact passage (5-40 words, verbatim from the transcription, "
        "no edits) that best supports it, or null if nothing in the document supports it. Return JSON "
        '{"<call>": "<verbatim passage or null>"}. Calls: ' + json.dumps(want)}], json_mode=True)
    try: return json.loads(t)
    except Exception: return {w: None for w in want}

def _norm(s): return re.sub(r"\s+", " ", (s or "").lower()).strip()

def verify(text, quote):
    if not quote: return False
    q, t = _norm(quote), _norm(text)
    return len(q) >= 15 and q in t

def review(path):
    t0 = time.time()
    text = read_page(path)
    dec = decide(path, text)
    ev = evidence(text, dec)
    checks = {k: {"quote": v, "verified": verify(text, v)} for k, v in ev.items()}
    resp = dec["p_responsive"] >= 0.5
    priv = dec["p_privileged"] >= 0.5
    conf = min(max(dec["p_responsive"], 1 - dec["p_responsive"]), max(dec["p_privileged"], 1 - dec["p_privileged"]))
    reasons = []
    if conf < THRESH: reasons.append(f"low confidence ({conf:.2f} < {THRESH})")
    for k, c in checks.items():
        if not c["verified"]: reasons.append(f"evidence for '{k}' not found verbatim on the page")
    return {"responsive": resp, "request": dec["request"] if resp else "none", "privileged": priv,
            "decision": "auto" if not reasons else "human_review", "reasons": reasons,
            "confidence": round(conf, 3), "probs": dec, "evidence": checks,
            "transcription": text, "seconds": round(time.time() - t0, 1)}

def baseline(path):
    mime, data = _img_part(path)
    t = _gen(BASELINE, [{"inline_data": {"mime_type": mime, "data": data}},
        {"text": "Review instructions:\n" + REQUESTS + '\n\nCode this scanned document. Return JSON {"responsive": true|false, '
                 '"request": "R1"|"R2"|"R3"|"none", "privileged": true|false}.'}], json_mode=True)
    try: return json.loads(t)
    except Exception: return {"responsive": None, "request": None, "privileged": None}

if __name__ == "__main__":
    import sys
    print(json.dumps(review(sys.argv[1]), indent=1)[:3000])
