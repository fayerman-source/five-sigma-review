# Agreement with model-made labels on 76 scans (NOT attorney labels)

## How the test set was chosen (read this first)
The set is 76 public Enron emails, rendered as degraded scans. 40 were found by keyword searches for terms that match the mock requests (Chewco, ISO congestion, LJM, Raptor, Vinson Elkins, Whitewing, document retention, mark to market earnings, price cap California, privileged confidential attorney); 36 were taken from random positions in the corpus. Keyword-picked documents are easier for any model, because the search term that found them is usually the reason they are responsive. So every number is given three ways: all documents, random only, keyword-picked only. **The random row is the fairer estimate of real-world performance.**

**These labels were made by a model (Gemini 4 Argon, given only the scan and the review instructions), not by a person.** So "right" below means "agrees with Gemini 4 Argon", which is weaker than accuracy: Gemini 4 Argon can be wrong, it is from the same model family as the system under test, and like the baseline it is a single model reading the page. Model outputs and the auto-decision threshold (0.9) were fixed and committed before the first label was saved. "Right" means all three calls match the reference model: responsive or not, which request, privileged or not.

| Documents | n | Single-call baseline right | Five Sigma right (all docs) | Five Sigma right (auto-decided only) | Decided without a human | Wrong but auto-decided |
|---|---|---|---|---|---|---|
| All labeled documents | 76 | 64/76 (84%) | 71/76 (93%) | 35/35 (100%) | 35/76 (46%) | 0 |
| Random documents | 36 | 35/36 (97%) | 34/36 (94%) | 21/21 (100%) | 21/36 (58%) | 0 |
| Keyword-picked documents | 40 | 29/40 (72%) | 37/40 (92%) | 14/14 (100%) | 14/40 (35%) | 0 |

95% intervals on all labeled documents: baseline 74%–91%, Five Sigma all docs 86%–97%, Five Sigma auto-decided 90%–100%. With samples this small the intervals are wide; read differences of a few documents as noise.

### All labeled documents (n = 76)
- Responsiveness, baseline: precision 100%, recall 97% (TP 30, FP 0, FN 1)
- Responsiveness, Five Sigma: precision 100%, recall 97% (TP 30, FP 0, FN 1)
- Privilege, baseline: precision 43%, recall 86% (TP 6, FP 8, FN 1)
- Privilege, Five Sigma: precision 71%, recall 71% (TP 5, FP 2, FN 2)
- Head to head: Five Sigma right where the baseline was wrong on 10; baseline right where Five Sigma was wrong on 3
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
- Privilege, baseline: precision 43%, recall 86% (TP 6, FP 8, FN 1)
- Privilege, Five Sigma: precision 83%, recall 71% (TP 5, FP 1, FN 2)
- Head to head: Five Sigma right where the baseline was wrong on 9; baseline right where Five Sigma was wrong on 1
- Wrong but auto-decided (the failures that matter): 0 []
- Wrong and routed to a human (caught): 3
- Right but routed to a human anyway (review cost): 23
