"""Compare the three single-pass model labelers (Argon, Carbon, Neon) and score against their majority; write eval/AGREEMENT.md."""
from collections import Counter
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = [("argon", "Argon"), ("carbon", "Carbon"), ("neon", "Neon")]
LABELS = {k: json.loads((ROOT / "eval" / f"labels_{k}.json").read_text()) for k, _ in NAMES}
RESULTS = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "eval" / "results.jsonl").open()}
EMAILS = [json.loads(l) for l in (ROOT / "data" / "emails.jsonl").open()]

def _text(e): return re.sub(r"\W+", " ", e["body"].lower()).strip()[:400]
_seen = {}
for e in EMAILS: _seen.setdefault(_text(e), e["doc_id"])
FIRST_COPY = set(_seen.values())  # same duplicate rule as src/score.py: first copy per normalised body text

def norm_call(c):
    resp = bool(c.get("responsive"))
    req = (c.get("request") or "none") if resp else "none"
    priv = bool(c.get("privileged"))
    return (resp, req, priv)

def fmt_call(t):
    resp, req, priv = t
    r_txt = f"responsive ({req})" if resp else "not responsive"
    p_txt = "privileged" if priv else "not privileged"
    return f"{r_txt}, {p_txt}"

def majority_call(calls):
    counts = Counter(calls)
    top, freq = counts.most_common(1)[0]
    if freq >= 2:
        return top
    resp = Counter(c[0] for c in calls).most_common(1)[0][0]
    req = Counter(c[1] for c in calls if c[0]).most_common(1)[0][0] if resp else "none"
    priv = Counter(c[2] for c in calls).most_common(1)[0][0]
    return (resp, req, priv)

def frac(k, n): return f"{k}/{n} ({k / n:.0%})" if n else "0/0"

def main():
    docs = sorted(set.intersection(*(set(d.keys()) for d in LABELS.values())))
    n = len(docs)
    pairs = [("argon", "carbon", "Argon vs Carbon"),
             ("argon", "neon", "Argon vs Neon"),
             ("carbon", "neon", "Carbon vs Neon")]

    pair_rows = []
    for a, b, label in pairs:
        same_all = sum(1 for d in docs if norm_call(LABELS[a][d]) == norm_call(LABELS[b][d]))
        same_r = sum(1 for d in docs if bool(LABELS[a][d]["responsive"]) == bool(LABELS[b][d]["responsive"]))
        same_q = sum(1 for d in docs if (LABELS[a][d].get("request") or "none") == (LABELS[b][d].get("request") or "none"))
        same_p = sum(1 for d in docs if bool(LABELS[a][d]["privileged"]) == bool(LABELS[b][d]["privileged"]))
        pair_rows.append((label, same_all, same_r, same_q, same_p))

    maj = {}
    split_docs = []
    for d in docs:
        ca, cc, cn = (norm_call(LABELS[k][d]) for k, _ in NAMES)
        m = majority_call([ca, cc, cn])
        maj[d] = m
        if not (ca == cc == cn):
            split_docs.append((d, ca, cc, cn, m))

    unanimous = n - len(split_docs)

    def score_subset(sub):
        sys_ok = base_ok = auto = auto_ok = wrong_auto = 0
        for d in sub:
            r = RESULTS[d]
            y, b, g = r["system"], r["baseline"], maj[d]
            oy = norm_call(y) == g
            ob = norm_call(b) == g
            sys_ok += oy
            base_ok += ob
            if y["decision"] == "auto":
                auto += 1
                auto_ok += oy
                wrong_auto += not oy
        return len(sub), base_ok, sys_ok, auto, auto_ok, wrong_auto

    all_stats = score_subset(docs)
    distinct_docs = [d for d in docs if d in FIRST_COPY]
    distinct_stats = score_subset(distinct_docs)

    lines = [
        f"# Agreement across three model labelers on {n} scans (NOT attorney labels)",
        "",
        "Three Gemini 4 models labeled all 76 degraded scans independently from the scan image and `data/requests.md` only: "
        "Gemini 4 Argon (`eval/labels_argon.json`), Gemini 4 Carbon (`eval/labels_carbon.json`), and Gemini 4 Neon (`eval/labels_neon.json`). "
        "**None of these is a human attorney.** Gemini 4 Neon is also the model used in Stage 3 of Five Sigma to extract supporting quotes, "
        "so it is less independent of the system than Argon and Carbon.",
        "",
        "## (a) Pairwise agreement on all three calls",
        "",
        "Two labelers agree on a document only when all three calls match (`responsive`, `request`, and `privileged`).",
        "",
        "| Pair | All three calls match | Responsiveness | Request | Privilege |",
        "|---|---|---|---|---|",
    ]
    for label, same_all, same_r, same_q, same_p in pair_rows:
        lines.append(f"| {label} | {frac(same_all, n)} | {frac(same_r, n)} | {frac(same_q, n)} | {frac(same_p, n)} |")
    lines += [
        "",
        f"All three labelers are unanimous on **{frac(unanimous, n)}** documents and split on **{len(split_docs)}**.",
        "",
        "## (b) & (c) Non-unanimous documents and majority label",
        "",
        "| Document | Argon | Carbon | Neon | Majority (2 of 3) |",
        "|---|---|---|---|---|",
    ]
    for d, ca, cc, cn, m in split_docs:
        lines.append(f"| {d} | {fmt_call(ca)} | {fmt_call(cc)} | {fmt_call(cn)} | {fmt_call(m)} |")

    lines += [
        "",
        "## (d) System and baseline against the 3-labeler majority",
        "",
        "Duplicate handling reuses `src/score.py` (first copy kept per normalised body text, leaving 61 distinct emails).",
        "",
        "| Subset | n | Single-call baseline matches majority | Five Sigma matches majority (all docs) | Five Sigma matches majority (auto-decided) | Decided without a human | Wrong but auto-decided |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, st in [("All documents", all_stats), ("Distinct emails only (first copy per normalised body)", distinct_stats)]:
        sn, base_ok, sys_ok, auto, auto_ok, wrong_auto = st
        lines.append(f"| {name} | {sn} | {frac(base_ok, sn)} | {frac(sys_ok, sn)} | {frac(auto_ok, auto)} | {frac(auto, sn)} | {wrong_auto} |")
    lines.append("")

    out = ROOT / "eval" / "AGREEMENT.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main()
