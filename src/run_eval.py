"""Run the 5 Sigma pipeline and the single-call baseline on every document, then score both
against the attorney's labels (eval/labels.json, written before any model output was viewed)."""
import json, sys, concurrent.futures as cf
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "results.jsonl"

def one(doc):
    img = ROOT / "data" / "scans" / f"{doc}.jpg"
    r = {"doc_id": doc}
    try: r["system"] = P.review(img)
    except Exception as e: r["system"] = {"error": str(e)[:300]}
    try: r["baseline"] = P.baseline(img)
    except Exception as e: r["baseline"] = {"error": str(e)[:300]}
    return r

def main():
    docs = [json.loads(l)["doc_id"] for l in (ROOT / "data" / "emails.jsonl").open()]
    done = {json.loads(l)["doc_id"] for l in OUT.open()} if OUT.exists() else set()
    todo = [d for d in docs if d not in done]
    with cf.ThreadPoolExecutor(6) as ex, OUT.open("a") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n"); f.flush(); print(r["doc_id"], "ok" if "error" not in r["system"] else r["system"]["error"][:80], flush=True)

if __name__ == "__main__":
    main()
