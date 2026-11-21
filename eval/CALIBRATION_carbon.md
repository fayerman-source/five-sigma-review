# Does the confidence mean anything?

Scored against labels made by a model (Gemini 4 Carbon), not by an attorney. "Matches" means agreement with those labels.

With 76 documents (61 distinct emails) the bins are small, so a bin's share can move a lot on one or two documents.

## Overall confidence and all three calls

The overall confidence is the lower of the two probabilities below. A document is decided without a human only at or above the threshold.

| System confidence | Documents | All three calls match the labels |
|---|---|---|
| below 0.7 | 13 | 10/13 (77%) |
| 0.7 to 0.8 | 17 | 15/17 (88%) |
| 0.8 to 0.9 | 11 | 11/11 (100%) |
| 0.9 to 0.95 | 14 | 14/14 (100%) |
| 0.95 and above | 21 | 21/21 (100%) |

## Each Decisions API probability on its own

Binned by the stated probability of the answer the system chose.

| Stated probability | Responsive: calls | Responsive: match the labels | Privileged: calls | Privileged: match the labels |
|---|---|---|---|---|
| below 0.7 | 3 | 3/3 (100%) | 10 | 7/10 (70%) |
| 0.7 to 0.8 | 8 | 7/8 (88%) | 10 | 9/10 (90%) |
| 0.8 to 0.9 | 10 | 10/10 (100%) | 8 | 8/8 (100%) |
| 0.9 to 0.95 | 14 | 14/14 (100%) | 5 | 5/5 (100%) |
| 0.95 and above | 41 | 41/41 (100%) | 43 | 43/43 (100%) |
