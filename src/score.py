"""Score system vs baseline against the attorney's labels; write eval/REPORT.md.

Results are given for all labeled documents and separately for the two ways documents were
picked (keyword search vs random row), because keyword-picked documents are easier."""
import json, math, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = os.environ.get("LABELS_FILE", "labels.json")
MODEL_LABELS = LABELS_FILE != "labels.json"  # anything but the attorney's file is a model labeler, and the report says so
TAG = "" if not MODEL_LABELS else "_" + Path(LABELS_FILE).stem.replace("labels_", "")
L = json.loads((ROOT / "eval" / LABELS_FILE).read_text()) if (ROOT / "eval" / LABELS_FILE).exists() else {}
R = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "eval" / "results.jsonl").open()}
E = [json.loads(l) for l in (ROOT / "data" / "emails.jsonl").open()]
GROUP = {e["doc_id"]: ("keyword" if e["source"].startswith("search:") else "random") for e in E}
QUERIES = sorted({e["source"].split(":", 1)[1] for e in E if e["source"].startswith("search:")})
def usable(r):
    """Both the system and the baseline produced an answer (same filter as sweep.py)."""
    return all(isinstance(r.get(k), dict) and "error" not in r[k] for k in ("system", "baseline"))
DOCS = sorted(d for d in L if d in R and usable(R[d]))

def cmp(pred, gold):
    return (pred.get("responsive") == gold["responsive"],
            (pred.get("request") or "none") == (gold.get("request") or "none"),
            bool(pred.get("privileged")) == bool(gold["privileged"]))

def prf(pairs):
    tp = sum(1 for p, g in pairs if p and g); fp = sum(1 for p, g in pairs if p and not g); fn = sum(1 for p, g in pairs if not p and g)
    p = f"{tp / (tp + fp):.0%}" if tp + fp else "n/a"; r = f"{tp / (tp + fn):.0%}" if tp + fn else "n/a"
    return f"precision {p}, recall {r} (TP {tp}, FP {fp}, FN {fn})"

def wilson(k, n, z=1.96):
    """95% Wilson interval for k right out of n, as text."""
    if not n: return "n/a"
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return f"{max(0.0, (c - h) / d):.0%}–{min(1.0, (c + h) / d):.0%}"

def frac(k, n): return f"{k}/{n} ({k / n:.0%})" if n else "0/0"

def stats(docs):
    s = dict(n=len(docs), base_ok=0, sys_ok=0, auto=0, auto_ok=0, wrong_auto=[], routed_bad=0, routed_ok=0,
             sys_only=0, base_only=0, br=[], sr=[], bp=[], sp=[])
    for d in docs:
        g, y, b = L[d], R[d]["system"], R[d]["baseline"]
        ob, oy = all(cmp(b, g)), all(cmp(y, g))
        s["base_ok"] += ob; s["sys_ok"] += oy; s["sys_only"] += oy and not ob; s["base_only"] += ob and not oy
        s["br"].append((bool(b.get("responsive")), g["responsive"])); s["sr"].append((y["responsive"], g["responsive"]))
        s["bp"].append((bool(b.get("privileged")), g["privileged"])); s["sp"].append((y["privileged"], g["privileged"]))
        if y["decision"] == "auto":
            s["auto"] += 1; s["auto_ok"] += oy
            if not oy: s["wrong_auto"].append(d)
        elif oy: s["routed_ok"] += 1
        else: s["routed_bad"] += 1
    return s

def row(name, s):
    n = s["n"]
    return (f"| {name} | {n} | {frac(s['base_ok'], n)} | {frac(s['sys_ok'], n)} | "
            f"{frac(s['auto_ok'], s['auto'])} | {frac(s['auto'], n)} | {len(s['wrong_auto'])} |")

def detail(name, s):
    return [f"### {name} (n = {s['n']})",
            f"- Responsiveness, baseline: {prf(s['br'])}", f"- Responsiveness, Five Sigma: {prf(s['sr'])}",
            f"- Privilege, baseline: {prf(s['bp'])}", f"- Privilege, Five Sigma: {prf(s['sp'])}",
            f"- Head to head: Five Sigma right where the baseline was wrong on {s['sys_only']}; baseline right where Five Sigma was wrong on {s['base_only']}",
            f"- Wrong but auto-decided (the failures that matter): {len(s['wrong_auto'])} {s['wrong_auto']}",
            f"- Wrong and routed to a human (caught): {s['routed_bad']}",
            f"- Right but routed to a human anyway (review cost): {s['routed_ok']}", ""]

def main():
    groups = [("All labeled documents", DOCS), ("Random documents", [d for d in DOCS if GROUP[d] == "random"]),
              ("Keyword-picked documents", [d for d in DOCS if GROUP[d] == "keyword"])]
    S = [(name, stats(docs)) for name, docs in groups]
    a = S[0][1]; n = a["n"]
    nk = sum(1 for g in GROUP.values() if g == "keyword")
    who = "the attorney" if not MODEL_LABELS else "the reference model"
    if MODEL_LABELS:
        title = f"# Agreement with model-made labels on {n} scans (NOT attorney labels)"
        how = ("**These labels were made by a model (Gemini 4 Carbon, through the labeling page, from the scan and the review "
               "instructions only), not by a person.** So \"right\" below means \"agrees with Gemini 4 Carbon\", which is weaker than "
               "accuracy: Carbon can be wrong, and it is from the same model family as the system under test. ")
    else:
        title = f"# Results on {n} attorney-labeled scans"
        how = "The attorney labeled the scans before seeing any model output. "
    lines = [title, "",
        "## How the test set was chosen (read this first)",
        f"The set is {len(GROUP)} public Enron emails, rendered as degraded scans. {nk} were found by keyword searches for terms "
        f"that match the mock requests ({', '.join(QUERIES)}); {len(GROUP) - nk} were taken from random positions in the corpus. "
        "Keyword-picked documents are easier for any model, because the search term that found them is usually the reason they are "
        "responsive. So every number is given three ways: all documents, random only, keyword-picked only. "
        "**The random row is the fairer estimate of real-world performance.**", "",
        how + "Model outputs and the auto-decision threshold (0.9) were "
        f"fixed and committed before the first label was saved. \"Right\" means all three calls match {who}: "
        "responsive or not, which request, privileged or not.", "",
        "| Documents | n | Single-call baseline right | Five Sigma right (all docs) | Five Sigma right (auto-decided only) | Decided without a human | Wrong but auto-decided |",
        "|---|---|---|---|---|---|---|"] + [row(name, s) for name, s in S] + ["",
        f"95% intervals on all labeled documents: baseline {wilson(a['base_ok'], n)}, Five Sigma all docs {wilson(a['sys_ok'], n)}, "
        f"Five Sigma auto-decided {wilson(a['auto_ok'], a['auto'])}. With samples this small the intervals are wide; "
        "read differences of a few documents as noise.", ""]
    for name, s in S: lines += detail(name, s)
    (ROOT / "eval" / f"REPORT{TAG}.md").write_text("\n".join(lines)); print("\n".join(lines))

if __name__ == "__main__":
    main()
