"""A sandboxed model labeler: one Gemini 4 model labels each scan from the image and the review instructions only.

It is given nothing else: not the email text, not how the document was picked, not any system or baseline output.
Its labels are a model's opinion, never attorney labels; score them with LABELS_FILE=labels_<name>.json so the
reports say so. Usage: python3 src/model_label.py <model> <name> [first_doc last_doc]
Example: python3 src/model_label.py gemini-4-argon argon 1 76   ->  eval/labels_argon.json (+ _notes.json)"""
import json, os, sys, concurrent.futures as cf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ("You are an attorney doing first-pass document review. Review instructions:\n" + P.REQUESTS +
          "\n\nRead the scanned page carefully and completely. It may be skewed, blurred, noisy, stamped or carry handwritten notes. "
          "Then code it under the review instructions only:\n"
          "- responsive: true if it concerns at least one request, else false\n"
          "- request: the one request it most concerns (R1, R2 or R3), or \"none\" if not responsive\n"
          "- privileged: true only for a confidential lawyer communication made to request or give legal advice, or one that reflects "
          "that advice; a confidentiality footer or a 'privileged' header alone is not enough\n"
          'Return JSON {"responsive": true|false, "request": "R1"|"R2"|"R3"|"none", "privileged": true|false, '
          '"ambiguous": true|false, "reason": "<one sentence>"}. Set ambiguous to true if a careful reviewer could reasonably disagree.')

def label(model, doc, prompt=PROMPT):
    mime, data = P._img_part(ROOT / "data" / "scans" / f"{doc}.jpg")
    for _ in range(3):
        try:
            d = json.loads(P._gen(model, [{"inline_data": {"mime_type": mime, "data": data}}, {"text": prompt}], json_mode=True, thinking="high"))
            resp, priv = d["responsive"], d["privileged"]
            if not isinstance(resp, bool) or not isinstance(priv, bool):
                raise ValueError(f"non-boolean label: responsive={resp!r}, privileged={priv!r}")
            req = d.get("request") if resp else "none"
            if resp and req not in ("R1", "R2", "R3"):
                raise ValueError(f"responsive but request={req!r}")
            return doc, {"responsive": resp, "request": req, "privileged": priv}, {"ambiguous": d.get("ambiguous") is True, "reason": str(d.get("reason", ""))[:300]}
        except Exception as e:
            err = str(e)[:200]
    return doc, None, {"error": err}

def _repo_file(raw):
    """Return a resolved file path strictly inside ROOT, or None if not an existing repo file."""
    root = ROOT.resolve()
    p = Path(raw)
    cand = (p if p.is_absolute() else root / p).resolve()
    if not cand.is_relative_to(root) or not str(cand).startswith(str(root) + os.sep):
        raise ValueError(f"path outside repository root: {raw}")
    return cand if cand.is_file() else None

def _build_prompt(guidance):
    if not guidance:
        return PROMPT
    gp = _repo_file(guidance)
    extra = gp.read_text().strip() if gp is not None else guidance.strip()
    return PROMPT + "\n\n" + extra

def _load_docs(docs_arg):
    if not docs_arg:
        return [json.loads(l)["doc_id"] for l in (ROOT / "data" / "emails.jsonl").open()]  # ids only; no other field is read
    dp = _repo_file(docs_arg)
    if dp is None:
        raise FileNotFoundError(f"docs file not found inside repository: {docs_arg}")
    return json.loads(dp.read_text())

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("name")
    ap.add_argument("bounds", nargs="*", type=int)
    ap.add_argument("--docs", help="Optional JSON file of doc IDs to label")
    ap.add_argument("--guidance", help="Optional extra review guidance text or file path")
    args = ap.parse_args()
    model, name = args.model, args.name
    lo, hi = (args.bounds[0], args.bounds[1]) if len(args.bounds) >= 2 else (1, 10**6)
    prompt = _build_prompt(args.guidance)
    out, notes_path = ROOT / "eval" / f"labels_{name}.json", ROOT / "eval" / f"labels_{name}_notes.json"
    L = json.loads(out.read_text()) if out.exists() else {}
    N = json.loads(notes_path.read_text()) if notes_path.exists() else {}
    docs = _load_docs(args.docs)
    todo = [d for d in docs if lo <= int(d.split("-")[1]) <= hi and d not in L]
    with cf.ThreadPoolExecutor(6) as ex:
        futs = [ex.submit(label, model, d, prompt) for d in todo]
        for fut in cf.as_completed(futs):
            doc, lab, note = fut.result()
            if lab: L[doc] = lab
            N[doc] = dict(note, model=model)
            out.write_text(json.dumps(dict(sorted(L.items())), indent=1)); notes_path.write_text(json.dumps(dict(sorted(N.items())), indent=1))
            print(doc, "ok" if lab else "FAILED " + note["error"], flush=True)
    print(f"done: {len(L)} labeled by {model}, {sum(1 for d in todo if d not in L)} failed", flush=True)

if __name__ == "__main__":
    main()
