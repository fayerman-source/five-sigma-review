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

    synth_path = ROOT / "eval" / "labels_synthetic25.json"
    notes25_path = ROOT / "eval" / "labels_synthetic25_notes.json"
    if synth_path.exists():
        L25 = json.loads(synth_path.read_text())
        N25 = json.loads(notes25_path.read_text()) if notes25_path.exists() else {}
        sdocs = sorted(d for d in L25 if d in maj)
        sn = len(sdocs)
        ag_a = sum(1 for d in sdocs if norm_call(L25[d]) == norm_call(LABELS["argon"][d]))
        ag_c = sum(1 for d in sdocs if norm_call(L25[d]) == norm_call(LABELS["carbon"][d]))
        ag_n = sum(1 for d in sdocs if norm_call(L25[d]) == norm_call(LABELS["neon"][d]))
        ag_m = sum(1 for d in sdocs if norm_call(L25[d]) == maj[d])
        s_sys = s_base = s_auto = s_auto_ok = 0
        auto_diffs = []
        diff25 = []
        for d in sdocs:
            g = norm_call(L25[d])
            y, b = RESULTS[d]["system"], RESULTS[d]["baseline"]
            yc = norm_call(y)
            oy, ob = yc == g, norm_call(b) == g
            s_sys += oy
            s_base += ob
            is_auto = y["decision"] == "auto"
            if is_auto:
                s_auto += 1
                s_auto_ok += oy
                if not oy:
                    auto_diffs.append((d, yc, g))
            if g != maj[d] or (is_auto and not oy):
                reason = (N25.get(d, {}).get("reason") or "").replace("|", "/")
                diff25.append((d, g, maj[d], yc, y["decision"], reason))
        if not auto_diffs:
            auto_diff_desc = "0 automatic decisions differ from synthetic25"
        elif all(yc[0] == g[0] and yc[2] == g[2] and yc[1] != g[1] for _, yc, g in auto_diffs):
            tags = {(g[1], yc[1]) for _, yc, g in auto_diffs}
            tag_note = f" ({next(iter(tags))[0]} instead of {next(iter(tags))[1]})" if len(tags) == 1 else ""
            auto_diff_desc = (f"{len(auto_diffs)} automatic decisions where the synthetic check gives a different request tag"
                              f"{tag_note}; responsiveness and privilege match")
        else:
            auto_diff_desc = f"{len(auto_diffs)} automatic decisions differ from synthetic25"
        lines += [
            "",
            f"## (e) Synthetic second-look check on {sn} contested-and-control scans (NOT attorney labels)",
            "",
            "**Disclosure: `eval/labels_synthetic25.json` was produced by a Gemini 4 model (`gemini-4-carbon`) given the extra guidance in `data/privilege_guidance.md` (`--docs eval/attorney_check_docs.json --guidance data/privilege_guidance.md`), NOT by a human attorney.** "
            "The 25 document IDs come from `eval/attorney_check_docs.json` (contested, disagreement, and control scans). "
            "Note on guidance scope: in addition to two privilege rules, item 3 of `data/privilege_guidance.md` instructed the model on LJM/partnership litigation holds and document-collection instructions to weigh whether the page primarily concerns `R1` (the partnership) or `R3` (document retention, preservation, or collection instructions). "
            "That instruction matters when reading the automatic-decision comparison below, because the two automatic decisions where `synthetic25` differs from Five Sigma (`DOC-062` and `DOC-071`, two copies of one LJM document-collection email) differ on that exact request tag (`R3` instead of `R1`), while responsiveness and privilege match.",
            "",
            "| Comparison on the 25 scans | Agreement |",
            "|---|---|",
            f"| synthetic25 matches Argon | {frac(ag_a, sn)} |",
            f"| synthetic25 matches Carbon | {frac(ag_c, sn)} |",
            f"| synthetic25 matches Neon | {frac(ag_n, sn)} |",
            f"| synthetic25 matches 3-model majority | {frac(ag_m, sn)} |",
            f"| Single-call baseline matches synthetic25 (all three calls) | {frac(s_base, sn)} |",
            f"| Five Sigma (all 25) matches synthetic25 (all three calls) | {frac(s_sys, sn)} |",
            f"| Five Sigma automatic decisions matching synthetic25 (all three calls) | {frac(s_auto_ok, s_auto)} |",
            f"| Five Sigma automatic decisions differing from synthetic25 | {auto_diff_desc} |",
            "",
        ]
        if diff25:
            lines += [
                "Documents where `synthetic25` differs from the 3-model majority or from a Five Sigma auto-decision:",
                "",
                "| Document | synthetic25 | 3-model majority | Five Sigma call | Routing | Synthetic note |",
                "|---|---|---|---|---|---|",
            ]
            for d, g, m, yc, dec, rsn in diff25:
                lines.append(f"| {d} | {fmt_call(g)} | {fmt_call(m)} | {fmt_call(yc)} | {dec} | {rsn} |")
        else:
            lines.append("`synthetic25` agrees with the 3-model majority on all 25 documents and has 0 disagreements with Five Sigma's auto-decisions.")

    lines.append("")

    out = ROOT / "eval" / "AGREEMENT.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main()
