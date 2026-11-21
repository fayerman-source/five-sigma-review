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
