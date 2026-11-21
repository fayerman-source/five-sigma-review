"""What we changed after seeing failures: the auto-decision threshold.

Replays stored model outputs (no new API calls) at several thresholds and reports, for each,
how many documents are decided without a human and how many of those are right.

To avoid tuning on the test set, the threshold is PICKED on DOC-001..050 and then REPORTED on
DOC-051..076, which the choice never saw. Writes eval/THRESHOLDS.md and eval/threshold_curve.png.
Usage: python3 src/sweep.py [--pick 0.95]   (default: pick_threshold() below)"""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = os.environ.get("LABELS_FILE", "labels.json")
MODEL_LABELS = LABELS_FILE != "labels.json"  # a model labeler, not the attorney; the report says so
TAG = "" if not MODEL_LABELS else "_" + Path(LABELS_FILE).stem.replace("labels_", "")
L = json.loads((ROOT / "eval" / LABELS_FILE).read_text()) if (ROOT / "eval" / LABELS_FILE).exists() else {}
ROWS = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "eval" / "results.jsonl").open()}
def usable(r):
    """Both the system and the baseline produced an answer (same filter as score.py)."""
    return all(isinstance(r.get(k), dict) and "error" not in r[k] for k in ("system", "baseline"))
R = {d: r["system"] for d, r in ROWS.items() if usable(r)}
GROUP = {json.loads(l)["doc_id"]: ("keyword" if json.loads(l)["source"].startswith("search:") else "random")
         for l in (ROOT / "data" / "emails.jsonl").open()}
DOCS = sorted(d for d in L if d in R)
THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99]
PREREGISTERED = 0.9
TUNE_MAX = 50  # DOC-001..050 pick the threshold; DOC-051.. confirm it

def right(d):
    s, g = R[d], L[d]
    return (s["responsive"] == g["responsive"] and (s["request"] or "none") == (g.get("request") or "none")
            and bool(s["privileged"]) == bool(g["privileged"]))

def evidence_ok(d): return all(c["verified"] for c in R[d]["evidence"].values())

def conf(d):
    """Unrounded confidence, computed exactly as pipeline.review() does (the stored "confidence" is rounded to 3 places)."""
    p = R[d]["probs"]
    return min(max(p["p_responsive"], 1 - p["p_responsive"]), max(p["p_privileged"], 1 - p["p_privileged"]))

def at(docs, t, use_evidence=True):
    """Counts at threshold t: documents decided automatically, how many of those are right or wrong."""
    auto = [d for d in docs if conf(d) >= t and (evidence_ok(d) or not use_evidence)]
    ok = sum(right(d) for d in auto)
    return {"t": t, "n": len(docs), "auto": len(auto), "ok": ok, "wrong": len(auto) - ok,
            "wrong_ids": [d for d in auto if not right(d)]}

def pick_threshold(rows):
    """The policy for choosing the operating threshold from the tuning rows (one row per threshold).

    Default policy: the lowest threshold with no wrong auto-decision on the tuning documents, i.e. as
    much automation as possible without an observed unreviewed error. If none qualifies, the strictest.
    This is a risk-tolerance decision (how many unreviewed errors a reviewing attorney accepts); edit here."""
    clean = [r["t"] for r in rows if r["wrong"] == 0 and r["auto"] > 0]
    return min(clean) if clean else max(r["t"] for r in rows)

def pct(k, n): return f"{k}/{n} ({k / n:.0%})" if n else "0/0"

def table(title, docs, mark=()):
    out = [f"### {title} (n = {len(docs)})", "",
           "| Threshold | Decided without a human | Auto-decided and right | Wrong but auto-decided | Same, without the quote check |", "|---|---|---|---|---|"]
    for t in THRESHOLDS:
        a, b = at(docs, t), at(docs, t, use_evidence=False)
        tag = " (pre-registered)" if t == PREREGISTERED else ""
        tag += " (picked)" if t in mark else ""
        out.append(f"| {t}{tag} | {pct(a['auto'], a['n'])} | {pct(a['ok'], a['auto'])} | {a['wrong']} {a['wrong_ids'] or ''} | "
                   f"{pct(b['auto'], b['n'])} decided, {b['wrong']} wrong |")
    return out + [""]

def chart(docs, picked, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [at(docs, t) for t in THRESHOLDS]
    x = list(range(len(THRESHOLDS)))
    cov = [100 * r["auto"] / r["n"] if r["n"] else None for r in rows]
    acc = [100 * r["ok"] / r["auto"] if r["auto"] else None for r in rows]
    ink, muted, grid, surface = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=160, facecolor=surface); ax.set_facecolor(surface)
    series = [("Decided without a human", cov, "#2a78d6"), ("Auto-decided calls that are right", acc, "#eb6834")]
    for name, ys, color in series:
        pts = [(i, y) for i, y in zip(x, ys) if y is not None]
        if not pts: continue
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=2, marker="o", ms=6, mec=surface, mew=1.5,
                solid_capstyle="round", solid_joinstyle="round", label=name, clip_on=False)
        ax.annotate(f"{pts[-1][1]:.0f}%", pts[-1], xytext=(9, 0), textcoords="offset points", va="center", color=ink, fontsize=10)
    for t, label in ((PREREGISTERED, "pre-registered"), (picked, "picked")):
        if t in THRESHOLDS and not (label == "picked" and picked == PREREGISTERED):
            i = THRESHOLDS.index(t); ax.axvline(i, color="#c9c8c3", lw=1, zorder=0)
            ax.annotate(label, (i, 3), xytext=(4, 0), textcoords="offset points", color=muted, fontsize=9, va="bottom")
    ax.set_xticks(x); ax.set_xticklabels([str(t) for t in THRESHOLDS]); ax.set_ylim(0, 104); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"]); ax.set_xlabel("Confidence required to decide without a human", color=muted)
    ax.yaxis.grid(True, color=grid, lw=1); ax.set_axisbelow(True); ax.tick_params(colors=muted, length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(f"Automation and accuracy at each confidence threshold (all labeled documents, n = {len(docs)})", color=ink, fontsize=11, loc="left", pad=28)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9, labelcolor=ink, borderaxespad=0.2)
    fig.tight_layout(); fig.savefig(path, facecolor=surface); plt.close(fig)

def main():
    tune = [d for d in DOCS if int(d.split("-")[1]) <= TUNE_MAX]
    confirm = [d for d in DOCS if int(d.split("-")[1]) > TUNE_MAX]
    picked = float(sys.argv[sys.argv.index("--pick") + 1]) if "--pick" in sys.argv else pick_threshold([at(tune, t) for t in THRESHOLDS])
    before, after = at(tune, PREREGISTERED), at(tune, picked)
    lines = ["# What we changed after seeing failures: the auto-decision threshold", ""]
    if MODEL_LABELS:
        lines += ["**Scored against labels made by a model (Gemini 4 Carbon), not by the attorney. \"Right\" and \"wrong\" here mean "
                  "agreement or disagreement with that model.**", ""]
    lines += [
        f"The system was run once, with the threshold fixed at {PREREGISTERED} before any label existed. After scoring, we replayed the "
        "stored outputs at other thresholds (no new model calls). A document is decided without a human only if its calibrated "
        "confidence is at or above the threshold AND every supporting quote is found verbatim on the page; the last column drops "
        "the quote check to show what that check adds.", "",
        f"To avoid tuning on the test set, the threshold was picked on DOC-001..{TUNE_MAX:03d} only, by this rule: the lowest threshold "
        f"with no wrong auto-decision. It was then checked on DOC-{TUNE_MAX + 1:03d} onward, which the choice never saw.", "",
        f"**Picked threshold: {picked}** (was {PREREGISTERED}).", "",
        "| | Decided without a human | Wrong but auto-decided |", "|---|---|---|",
        f"| Tuning documents, before ({PREREGISTERED}) | {pct(before['auto'], before['n'])} | {before['wrong']} |",
        f"| Tuning documents, after ({picked}) | {pct(after['auto'], after['n'])} | {after['wrong']} |"]
    if confirm:
        cb, ca = at(confirm, PREREGISTERED), at(confirm, picked)
        lines += [f"| Confirmation documents, before ({PREREGISTERED}) | {pct(cb['auto'], cb['n'])} | {cb['wrong']} {cb['wrong_ids'] or ''} |",
                  f"| Confirmation documents, after ({picked}) | {pct(ca['auto'], ca['n'])} | {ca['wrong']} {ca['wrong_ids'] or ''} |"]
    else:
        lines += ["", f"No documents after DOC-{TUNE_MAX:03d} are labeled yet, so the picked threshold is NOT confirmed on unseen documents."]
    lines += ["", f"![Threshold curve](threshold_curve{TAG}.png)", ""]
    lines += table("Tuning documents", tune, mark=(picked,))
    if confirm: lines += table("Confirmation documents (never used to pick)", confirm, mark=(picked,))
    lines += table("All labeled, random documents only", [d for d in DOCS if GROUP[d] == "random"], mark=(picked,))
    lines += table("All labeled, keyword-picked documents only", [d for d in DOCS if GROUP[d] == "keyword"], mark=(picked,))
    (ROOT / "eval" / f"THRESHOLDS{TAG}.md").write_text("\n".join(lines))
    chart(DOCS, picked, ROOT / "eval" / f"threshold_curve{TAG}.png")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
