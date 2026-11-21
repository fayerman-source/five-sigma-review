# Agreement across three model labelers on 76 scans (NOT attorney labels)

Three Gemini 4 models labeled all 76 degraded scans independently from the scan image and `data/requests.md` only: Gemini 4 Argon (`eval/labels_argon.json`), Gemini 4 Carbon (`eval/labels_carbon.json`), and Gemini 4 Neon (`eval/labels_neon.json`). **None of these is a human attorney.** Gemini 4 Neon is also the model used in Stage 3 of Five Sigma to extract supporting quotes, so it is less independent of the system than Argon and Carbon.

## (a) Pairwise agreement on all three calls

Two labelers agree on a document only when all three calls match (`responsive`, `request`, and `privileged`).

| Pair | All three calls match | Responsiveness | Request | Privilege |
|---|---|---|---|---|
| Argon vs Carbon | 72/76 (95%) | 76/76 (100%) | 76/76 (100%) | 72/76 (95%) |
| Argon vs Neon | 67/76 (88%) | 76/76 (100%) | 73/76 (96%) | 70/76 (92%) |
| Carbon vs Neon | 71/76 (93%) | 76/76 (100%) | 73/76 (96%) | 74/76 (97%) |

All three labelers are unanimous on **67/76 (88%)** documents and split on **9**.

## (b) & (c) Non-unanimous documents and majority label

| Document | Argon | Carbon | Neon | Majority (2 of 3) |
|---|---|---|---|---|
| DOC-020 | responsive (R1), not privileged | responsive (R1), not privileged | responsive (R3), not privileged | responsive (R1), not privileged |
| DOC-026 | responsive (R1), not privileged | responsive (R1), not privileged | responsive (R1), privileged | responsive (R1), not privileged |
| DOC-040 | responsive (R1), privileged | responsive (R1), not privileged | responsive (R1), not privileged | responsive (R1), not privileged |
| DOC-051 | responsive (R3), not privileged | responsive (R3), privileged | responsive (R3), privileged | responsive (R3), privileged |
| DOC-055 | responsive (R3), not privileged | responsive (R3), privileged | responsive (R3), privileged | responsive (R3), privileged |
| DOC-062 | responsive (R1), not privileged | responsive (R1), not privileged | responsive (R3), not privileged | responsive (R1), not privileged |
| DOC-065 | responsive (R3), privileged | responsive (R3), privileged | responsive (R3), not privileged | responsive (R3), privileged |
| DOC-071 | responsive (R1), not privileged | responsive (R1), not privileged | responsive (R3), not privileged | responsive (R1), not privileged |
| DOC-072 | responsive (R3), not privileged | responsive (R3), privileged | responsive (R3), privileged | responsive (R3), privileged |

## (d) System and baseline against the 3-labeler majority

Duplicate handling reuses `src/score.py` (first copy kept per normalised body text, leaving 61 distinct emails).

| Subset | n | Single-call baseline matches majority | Five Sigma matches majority (all docs) | Five Sigma matches majority (auto-decided) | Decided without a human | Wrong but auto-decided |
|---|---|---|---|---|---|---|
| All documents | 76 | 68/76 (89%) | 71/76 (93%) | 35/35 (100%) | 35/76 (46%) | 0 |
| Distinct emails only (first copy per normalised body) | 61 | 55/61 (90%) | 56/61 (92%) | 30/30 (100%) | 30/61 (49%) | 0 |

## (e) Synthetic second-look check on 25 contested-and-control scans (NOT attorney labels)

**Disclosure: `eval/labels_synthetic25.json` was produced by a Gemini 4 model (`gemini-4-carbon`) given extra scrutiny guidance on privilege boundaries and LJM litigation holds, NOT by a human attorney.** The 25 document IDs come from `eval/attorney_check_docs.json` (contested, disagreement, and control scans).

| Comparison on the 25 scans | Match count |
|---|---|
| synthetic25 vs Argon | 21/25 (84%) |
| synthetic25 vs Carbon | 19/25 (76%) |
| synthetic25 vs Neon | 20/25 (80%) |
| synthetic25 vs 3-model majority | 19/25 (76%) |
| Single-call baseline vs synthetic25 | 17/25 (68%) |
| Five Sigma (all 25) vs synthetic25 | 16/25 (64%) |
| Five Sigma (auto-decided) vs synthetic25 | 6/8 (75%) (2 wrong auto-decisions) |

Documents where `synthetic25` differs from the 3-model majority or from a Five Sigma auto-decision:

| Document | synthetic25 | 3-model majority | Five Sigma call | Routing | Synthetic note |
|---|---|---|---|---|---|
| DOC-034 | responsive (R1), privileged | responsive (R1), not privileged | responsive (R1), not privileged | human_review | In-house Enron counsel Mary Cook analyzes Chewco and JEDI I ownership percentages to assist colleagues in reviewing Raptor matters, making it responsive to R1 and privileged (though somewhat ambiguous given the underlying factual information from a non-lawyer). |
| DOC-040 | responsive (R1), privileged | responsive (R1), not privileged | responsive (R1), not privileged | human_review | The email directly concerns Chewco and Raptor investments (R1), and is sent by in-house counsel Mary Cook analyzing entity ownership interests to assist in reviewing Raptor matters, though it closely borders on relaying factual business information. |
| DOC-055 | responsive (R3), not privileged | responsive (R3), privileged | responsive (R3), not privileged | human_review | The email chain directly concerns ENA and EES document retention policies regarding post-closing drafts (R3), and while exchanged between in-house legal personnel, it merely makes a factual inquiry about policy status and refers the sender to a paralegal rather than conveying substantive legal advic |
| DOC-062 | responsive (R3), not privileged | responsive (R1), not privileged | responsive (R1), not privileged | auto | The email chain primarily concerns document-collection and preservation instructions—identifying Lotus Notes folders to burn to CDs and compiling hard copies for LJM litigation production (R3)—rather than substantive LJM partnership matters (R1), and it is not privileged because it addresses collect |
| DOC-071 | responsive (R3), not privileged | responsive (R1), not privileged | responsive (R1), not privileged | auto | The email chain concerns document-collection instructions and logistics (burning Lotus Notes folders to CDs and compiling hard copies) for LJM litigation rather than substantive LJM business or legal advice, though the LJM subject line and 'call legal re this' note create borderline R1 and privilege |
| DOC-072 | responsive (R3), not privileged | responsive (R3), privileged | responsive (R3), privileged | human_review | The email chain directly concerns ENA and EES document retention policies regarding transaction drafts (R3), and while exchanged between in-house legal personnel, it involves factual policy inquiries and a referral to a paralegal rather than substantive legal advice. |
