# Agreement with model-made labels on 76 scans (NOT attorney labels)

## How the test set was chosen (read this first)
The set is 76 public Enron emails, rendered as degraded scans. 40 were found by keyword searches for terms that match the mock requests (Chewco, ISO congestion, LJM, Raptor, Vinson Elkins, Whitewing, document retention, mark to market earnings, price cap California, privileged confidential attorney); 36 were taken from random positions in the corpus. Keyword-picked documents are easier for any model, because the search term that found them is usually the reason they are responsive. So every number is given three ways: all documents, random only, keyword-picked only. **The random row is the fairer estimate of real-world performance.**

**Duplicates.** The corpus stores the same email in several mailboxes, and 15 of the 76 test documents repeat the text of another one (all among the keyword-picked documents), so the set holds 61 distinct emails. Each copy is a different degraded scan, but they are not independent tests. The last row counts each distinct email once.

**These labels were made by a model (Gemini 4 Carbon, given only the scan and the review instructions), not by a person.** So "right" below means "agrees with Gemini 4 Carbon", which is weaker than accuracy: Gemini 4 Carbon can be wrong, it is from the same model family as the system under test, and like the baseline it is a single model reading the page. Model outputs and the auto-decision threshold (0.9) were fixed and committed before the first label was saved. "Right" means all three calls match the reference model: responsive or not, which request, privileged or not.

| Documents | n | Single-call baseline right | Five Sigma right (all docs) | Five Sigma right (auto-decided only) | Decided without a human | Wrong but auto-decided |
|---|---|---|---|---|---|---|
| All labeled documents | 76 | 68/76 (89%) | 71/76 (93%) | 35/35 (100%) | 35/76 (46%) | 0 |
| Random documents | 36 | 35/36 (97%) | 34/36 (94%) | 21/21 (100%) | 21/36 (58%) | 0 |
| Keyword-picked documents | 40 | 33/40 (82%) | 37/40 (92%) | 14/14 (100%) | 14/40 (35%) | 0 |
| Distinct emails only (each duplicate counted once) | 61 | 55/61 (90%) | 56/61 (92%) | 30/30 (100%) | 30/61 (49%) | 0 |

95% intervals on all labeled documents: baseline 81%–95%, Five Sigma all docs 86%–97%, Five Sigma auto-decided 90%–100%. With samples this small the intervals are wide; read differences of a few documents as noise.

### All labeled documents (n = 76)
- Responsiveness, baseline: precision 100%, recall 97% (TP 30, FP 0, FN 1)
- Responsiveness, Five Sigma: precision 100%, recall 97% (TP 30, FP 0, FN 1)
- Privilege, baseline: precision 64%, recall 100% (TP 9, FP 5, FN 0)
- Privilege, Five Sigma: precision 86%, recall 67% (TP 6, FP 1, FN 3)
- Head to head: Five Sigma right where the baseline was wrong on 8; baseline right where Five Sigma was wrong on 5
- Wrong but auto-decided (the failures that matter): 0 []
- Wrong and routed to a human (caught): 5
- Right but routed to a human anyway (review cost): 36

### Random documents (n = 36)
- Responsiveness, baseline: precision 100%, recall 67% (TP 2, FP 0, FN 1)
- Responsiveness, Five Sigma: precision 100%, recall 67% (TP 2, FP 0, FN 1)
- Privilege, baseline: precision n/a, recall n/a (TP 0, FP 0, FN 0)
- Privilege, Five Sigma: precision 0%, recall n/a (TP 0, FP 1, FN 0)
- Head to head: Five Sigma right where the baseline was wrong on 1; baseline right where Five Sigma was wrong on 2
- Wrong but auto-decided (the failures that matter): 0 []
- Wrong and routed to a human (caught): 2
- Right but routed to a human anyway (review cost): 13

### Keyword-picked documents (n = 40)
- Responsiveness, baseline: precision 100%, recall 100% (TP 28, FP 0, FN 0)
- Responsiveness, Five Sigma: precision 100%, recall 100% (TP 28, FP 0, FN 0)
- Privilege, baseline: precision 64%, recall 100% (TP 9, FP 5, FN 0)
- Privilege, Five Sigma: precision 100%, recall 67% (TP 6, FP 0, FN 3)
- Head to head: Five Sigma right where the baseline was wrong on 7; baseline right where Five Sigma was wrong on 3
- Wrong but auto-decided (the failures that matter): 0 []
- Wrong and routed to a human (caught): 3
- Right but routed to a human anyway (review cost): 23

### Distinct emails only (each duplicate counted once) (n = 61)
- Responsiveness, baseline: precision 100%, recall 95% (TP 18, FP 0, FN 1)
- Responsiveness, Five Sigma: precision 100%, recall 95% (TP 18, FP 0, FN 1)
- Privilege, baseline: precision 56%, recall 100% (TP 5, FP 4, FN 0)
- Privilege, Five Sigma: precision 67%, recall 40% (TP 2, FP 1, FN 3)
- Head to head: Five Sigma right where the baseline was wrong on 6; baseline right where Five Sigma was wrong on 5
- Wrong but auto-decided (the failures that matter): 0 []
- Wrong and routed to a human (caught): 5
- Right but routed to a human anyway (review cost): 26
