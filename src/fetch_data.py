"""Pull a sample of public Enron emails (corbt/enron-emails on Hugging Face) for the test set.
Mix of topic searches (so some documents are responsive) and random rows (so most are not)."""
import json, random, time, urllib.parse, urllib.request
from pathlib import Path

DS = "corbt/enron-emails"
BASE = "https://datasets-server.huggingface.co"
OUT = Path(__file__).resolve().parent.parent / "data" / "emails.jsonl"

def get(url):
    for _ in range(6):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                d = json.load(r)
            if "error" in d and "loading" in d["error"]:
                time.sleep(8); continue
            return d
        except Exception as e:
            time.sleep(4)
    return {}

def ok(row):
    b = (row.get("body") or "").strip()
    return 250 <= len(b) <= 2200 and "-----Original Message" not in b[:40]

def main():
    random.seed(21)
    picked, seen = [], set()
    def add(row, src):
        if row["message_id"] in seen or not ok(row): return False
        seen.add(row["message_id"]); row["source"] = src; picked.append(row); return True
    queries = ["LJM", "Raptor", "Chewco", "price cap California", "ISO congestion", "Vinson Elkins",
               "privileged confidential attorney", "document retention", "mark to market earnings", "Whitewing"]
    for q in queries:
        d = get(f"{BASE}/search?dataset={DS}&config=default&split=train&query={urllib.parse.quote(q)}&offset=0&length=40")
        n = 0
        for it in d.get("rows", []):
            if add(it["row"], f"search:{q}"): n += 1
            if n >= 4: break
        print(q, n, flush=True)
    for _ in range(12):
        off = random.randrange(0, 517000)
        d = get(f"{BASE}/rows?dataset={DS}&config=default&split=train&offset={off}&length=60")
        n = 0
        for it in d.get("rows", []):
            if add(it["row"], "random"): n += 1
            if n >= 3: break
    random.shuffle(picked)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w") as f:
        for i, r in enumerate(picked):
            r["doc_id"] = f"DOC-{i+1:03d}"
            f.write(json.dumps(r) + "\n")
    print("wrote", len(picked), OUT)

if __name__ == "__main__":
    main()
