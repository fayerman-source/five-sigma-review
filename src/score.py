"""Score system vs baseline against the attorney's labels; write eval/REPORT.md."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
L = json.loads((ROOT / "eval" / "labels.json").read_text())
R = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "eval" / "results.jsonl").open()}
docs = [d for d in L if d in R]

def cmp(pred, gold):
    return (pred.get("responsive") == gold["responsive"],
            (pred.get("request") or "none") == (gold.get("request") or "none"),
            bool(pred.get("privileged")) == bool(gold["privileged"]))

def pr(pairs):
    tp = sum(1 for p, g in pairs if p and g); fp = sum(1 for p, g in pairs if p and not g); fn = sum(1 for p, g in pairs if not p and g)
    return tp, fp, fn

rows, base_ok, sys_ok, auto, auto_ok, wrong_auto, routed_bad = [], 0, 0, 0, 0, [], 0
br, sr, bp, sp = [], [], [], []
for d in docs:
    g, s, b = L[d], R[d]["system"], R[d]["baseline"]
    if "error" in s or "error" in b: continue
    cb, cs = cmp(b, g), cmp(s, g)
    base_ok += all(cb); sys_ok += all(cs)
    br.append((bool(b.get("responsive")), g["responsive"])); sr.append((s["responsive"], g["responsive"]))
    bp.append((bool(b.get("privileged")), g["privileged"])); sp.append((s["privileged"], g["privileged"]))
    if s["decision"] == "auto":
        auto += 1; auto_ok += all(cs)
        if not all(cs): wrong_auto.append(d)
    elif not all(cs): routed_bad += 1
n = len(br)
def fmt(tp, fp, fn): 
    p = tp / (tp + fp) if tp + fp else 1.0; r = tp / (tp + fn) if tp + fn else 1.0
    return f"precision {p:.0%}, recall {r:.0%} (TP {tp}, FP {fp}, FN {fn})"
lines = [f"# Results on {n} attorney-labeled scans", "",
 "| | Single-call baseline | Five Sigma (all docs) | Five Sigma auto-decided only |", "|---|---|---|---|",
 f"| All three calls right | {base_ok}/{n} ({base_ok/n:.0%}) | {sys_ok}/{n} ({sys_ok/n:.0%}) | {auto_ok}/{auto} ({(auto_ok/auto if auto else 0):.0%}) |",
 f"| Share of docs decided without a human | 100% | — | {auto}/{n} ({auto/n:.0%}) |", "",
 f"- Responsiveness, baseline: {fmt(*pr(br))}", f"- Responsiveness, Five Sigma: {fmt(*pr(sr))}",
 f"- Privilege, baseline: {fmt(*pr(bp))}", f"- Privilege, Five Sigma: {fmt(*pr(sp))}",
 f"- Wrong but auto-decided (the failures that matter): {len(wrong_auto)} {wrong_auto}",
 f"- Wrong and routed to a human (caught): {routed_bad}"]
(ROOT / "eval" / "REPORT.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))
