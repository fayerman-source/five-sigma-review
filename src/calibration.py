"""Does the confidence mean anything? Agreement with the labels, by confidence bin.

Replays stored model outputs (no new API calls). Table 1 bins documents by the system's overall
confidence and counts how many of its calls match the labels on all three calls. Table 2 does the
same for each Decisions API probability on its own (responsive, privileged), using the stated
probability of the answer it chose. Writes eval/CALIBRATION.md (or CALIBRATION_<name>.md).
Usage: LABELS_FILE=labels_argon.json python3 src/calibration.py"""
import json, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = os.environ.get("LABELS_FILE", "labels.json")
MODEL_LABELS = LABELS_FILE != "labels.json"  # a model labeler, not the attorney; the report says so
TAG = "" if not MODEL_LABELS else "_" + Path(LABELS_FILE).stem.replace("labels_", "")
L = json.loads((ROOT / "eval" / LABELS_FILE).read_text()) if (ROOT / "eval" / LABELS_FILE).exists() else {}
ROWS = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "eval" / "results.jsonl").open()}
def usable(r):
    """Both the system and the baseline produced an answer (same filter as score.py and sweep.py)."""
    return all(isinstance(r.get(k), dict) and "error" not in r[k] for k in ("system", "baseline"))
R = {d: r["system"] for d, r in ROWS.items() if usable(r)}
DOCS = sorted(d for d in L if d in R)
_E = [json.loads(l) for l in (ROOT / "data" / "emails.jsonl").open()]
DISTINCT = len({re.sub(r"\W+", " ", e["body"].lower()).strip()[:400] for e in _E if e["doc_id"] in DOCS})
BINS = [(0.0, 0.7, "below 0.7"), (0.7, 0.8, "0.7 to 0.8"), (0.8, 0.9, "0.8 to 0.9"), (0.9, 0.95, "0.9 to 0.95"), (0.95, 1.01, "0.95 and above")]

def right(d):
    s, g = R[d], L[d]
    return (s["responsive"] == g["responsive"] and (s["request"] or "none") == (g.get("request") or "none")
            and bool(s["privileged"]) == bool(g["privileged"]))

def conf(d):
    """Unrounded confidence, computed exactly as pipeline.review() does."""
    p = R[d]["probs"]
    return min(max(p["p_responsive"], 1 - p["p_responsive"]), max(p["p_privileged"], 1 - p["p_privileged"]))

def one(d, key, field):
    """For a single yes/no question: (stated probability of the chosen answer, does the chosen answer match the label)."""
    p = R[d]["probs"][key]
    return max(p, 1 - p), (p >= 0.5) == bool(L[d][field])

def pct(k, n): return f"{k}/{n} ({k / n:.0%})" if n else "0/0"

def rows(pairs):
    """pairs: (confidence, matched) per item -> one table row per bin."""
    out = []
    for lo, hi, name in BINS:
        hit = [m for c, m in pairs if lo <= c < hi]
        out.append(f"| {name} | {len(hit)} | {pct(sum(hit), len(hit))} |")
    return out

def main():
    who = "the attorney's labels" if not MODEL_LABELS else f"labels made by a model (Gemini 4 {TAG.strip('_').capitalize()}), not by an attorney"
    lines = ["# Does the confidence mean anything?", "",
        f"Scored against {who}. \"Matches\" means agreement with those labels.", "",
        f"With {len(DOCS)} documents ({DISTINCT} distinct emails) the bins are small, so a bin's share can move a lot on one or two documents.", "",
        "## Overall confidence and all three calls", "",
        "The overall confidence is the lower of the two probabilities below. A document is decided without a human only at or above the threshold.", "",
        "| System confidence | Documents | All three calls match the labels |", "|---|---|---|"] + rows([(conf(d), right(d)) for d in DOCS]) + ["",
        "## Each Decisions API probability on its own", "",
        "Binned by the stated probability of the answer the system chose.", "",
        "| Stated probability | Responsive: calls | Responsive: match the labels | Privileged: calls | Privileged: match the labels |", "|---|---|---|---|---|"]
    a, b = rows([one(d, "p_responsive", "responsive") for d in DOCS]), rows([one(d, "p_privileged", "privileged") for d in DOCS])
    lines += [x.rstrip("|").rstrip() + " |" + y.split("|", 2)[2] for x, y in zip(a, b)] + [""]
    (ROOT / "eval" / f"CALIBRATION{TAG}.md").write_text("\n".join(lines)); print("\n".join(lines))

if __name__ == "__main__":
    main()
