# Five Sigma Review

First-pass legal document review of scanned pages. It says when it is not sure. Built at the Gemini 4 NYC Hackathon (Nov 21, 2026), Problem Statement One.

## The problem

In litigation, lawyers code thousands of documents. For each one they decide whether it is responsive to a document request, which request, and whether it is privileged. Models do this fast, but a wrong privilege call that nobody looks at can waive privilege. A reviewer needs to know which calls can be trusted without checking and which cannot.

## What it does

The input is one scanned page: a photo, a scan or a PDF. Three Gemini 4 models each do one job, and then code checks their work:

| Stage | Model | Job |
|---|---|---|
| 1. Read | `gemini-4-hydrogen` | Transcribe the page exactly, including stamps and handwriting |
| 2. Decide | Decisions API, `gemini-decision-1` | A probability for each call (responsive, which request, privileged), based on the image and the transcription |
| 3. Evidence | `gemini-4-neon` | For each positive call, the exact quote that supports it |
| 4. Check | plain code | Every quote must appear verbatim in the transcription |

A document is decided automatically only if confidence is at or above a threshold **and** every quote is verified. Anything else goes to a human with the reason. The system fails closed.

**Baseline:** one `gemini-4-hydrogen` call on the same image that answers all three questions at once.

## How it was tested

- **Documents:** 76 public Enron emails (Hugging Face `corbt/enron-emails`), each rendered as a page and degraded by `src/scan.py` (skew, blur, noise, fax header, Bates stamp, margin note in a handwriting font, perspective).
- **Requests:** three mock document requests and a privilege rule, in `data/requests.md`.
- **Labels:** made in a labeling page that shows only the scan, before the labeler sees any model output. The Results section says who made them.
- **Order of events, checkable in the git history:** model outputs for all 76 documents (`eval/results.jsonl`) were committed before the first label was saved. The scorer and the rule for picking a new threshold were also committed before the first label. The threshold in that run was 0.9.
- **Two runs, one scored:** the first run (12:15) used a personal API key instead of the hackathon one. We ran everything again on the hackathon key and committed that run at 12:50. No label existed yet, and we never scored the first run or compared it with the second. Only the second run is scored. The first is in the git history.

### How the test set was chosen: a known limitation

Of the 76 documents, 40 were found by keyword searches for terms that match the requests (for example `LJM`, `Raptor` and `document retention`). The other 36 came from random positions in the corpus. Keyword-picked documents are easier for any model, because the search term is usually what makes them responsive. So results are reported three ways: all documents, random only, and keyword-picked only. The random group is the fairer estimate.

## Results

Pending: labeling is not finished. This section will hold the table from `eval/REPORT.md` and will say who made the labels.

## What we changed after seeing failures

Pending. The plan was fixed in advance in `src/sweep.py`:

1. Replay the stored outputs at other thresholds.
2. Pick the lowest threshold with no wrong auto-decision on DOC-001 to DOC-050.
3. Report that threshold on DOC-051 onward. Those documents play no part in the choice.

## Where it still fails

Pending the scored failures. These limits are already known:

- The scans are synthetic. Real paper scans and real handwriting will be harder.
- There is one labeler, so there is no agreement rate.
- The sample is small. Differences of a few documents are noise.
- Each document is one page, and all are short emails (250 to 2,200 characters).
- The Enron corpus is public and widely used, so the models may have seen these emails in training.
- The quote check proves the quote is on the page as transcribed. It does not prove the quote supports the call, and it cannot catch a transcription error that the quote repeats.

## Run it

```
pip install -r requirements.txt
echo "GEMINI_API_KEY=..." > .env          # or .env.hackathon; both are gitignored
python3 src/app.py                        # live demo: http://127.0.0.1:8801
python3 src/run_eval.py                   # system and baseline on every scan -> eval/results.jsonl
python3 src/label_app.py                  # labeling page: http://127.0.0.1:8800 -> eval/labels.json
python3 src/score.py                      # -> eval/REPORT.md
python3 src/sweep.py                      # -> eval/THRESHOLDS.md, eval/threshold_curve.png
```

The live demo differs from the scored run in three ways. None of them affects the evaluation:

- It normalizes uploads first (rotates phone photos upright and shrinks them to 2,200 pixels on the long side).
- Its three sample scans (`data/samples/`) are public Enron emails that are not among the 76 test documents.
- It has an optional box for typing your own request, which replaces the three built-in ones for that page. The evaluation used only the built-in requests.

Public data only. Not legal advice.
