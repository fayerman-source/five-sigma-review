"""Render each email as a printed page, then degrade it like a real exhibit scan:
skew, blur, noise, JPEG artifacts, fax header, Bates stamp, occasional handwritten margin note,
and some pages 'photographed' with perspective and uneven light. Deterministic per doc."""
import json, random, textwrap, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
MONO = str(FONTS / "cour.ttf") if (FONTS / "cour.ttf").exists() else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
HAND = next((str(p) for p in (
    FONTS / "Inkfree.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
) if p.exists()), "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
NOTES = ["call legal re this", "?? who approved", "keep - JS", "see attached", "FYI only", "not for distribution",
         "follow up w/ Andy", "per our call", "dup?", "draft"]

def render(row, rnd):
    W, H = 1700, 2200
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    body_font = ImageFont.truetype(rnd.choice([SERIF, MONO]), 30)
    hdr = ImageFont.truetype(SERIF, 30)
    y = 140
    if rnd.random() < 0.4:  # fax header
        f = ImageFont.truetype(MONO, 22)
        d.text((80, 50), f"FROM: ENRON CORP  {row['date'][:10]}  {rnd.randint(10,23)}:{rnd.randint(10,59)}  P.{rnd.randint(1,3)}/{rnd.randint(3,6)}", font=f, fill=60)
    to = row["to"] if isinstance(row["to"], str) else ", ".join(row["to"])
    to = to.strip("[]").replace("'", "")[:110]
    for label, val in [("From:", row["from"]), ("Sent:", row["date"][:16].replace("T", " ")), ("To:", to), ("Subject:", row["subject"][:90])]:
        d.text((120, y), label, font=hdr, fill=0); d.text((300, y), val, font=hdr, fill=0); y += 44
    d.line((120, y + 10, W - 120, y + 10), fill=0, width=2); y += 40
    for para in row["body"].replace("\r", "").split("\n"):
        for line in (textwrap.wrap(para, 78) or [""]):
            if y > H - 200: break
            d.text((120, y), line, font=body_font, fill=rnd.randint(0, 40)); y += 40
    bates = ImageFont.truetype(SERIF, 26)
    d.text((W - 420, H - 110), f"EC-{rnd.randint(100000, 999999):06d}", font=bates, fill=0)
    if rnd.random() < 0.35:  # handwritten margin note
        hf = ImageFont.truetype(HAND, rnd.randint(44, 58))
        note = Image.new("L", (700, 120), 255); ImageDraw.Draw(note).text((5, 5), rnd.choice(NOTES), font=hf, fill=30)
        note = note.rotate(rnd.uniform(-12, 12), expand=True, fillcolor=255)
        img.paste(note, (W - 760, 40), note.point(lambda p: 255 if p < 128 else 0))
    return img

def degrade(img, rnd):
    img = img.rotate(rnd.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=False, fillcolor=255)
    if rnd.random() < 0.5: img = img.filter(ImageFilter.GaussianBlur(rnd.uniform(0.6, 1.4)))
    a = np.asarray(img).astype(np.float32)
    a += np.random.default_rng(rnd.randint(0, 10**6)).normal(0, rnd.uniform(6, 16), a.shape)
    if rnd.random() < 0.3:  # photographed: uneven light
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        a *= 0.75 + 0.25 * (xx / a.shape[1]) * (1 - 0.3 * yy / a.shape[0])
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if rnd.random() < 0.25:  # perspective (phone photo)
        w, h = img.size; k = rnd.uniform(30, 90)
        img = img.transform((w, h), Image.QUAD, (k, 0, 0, h, w, h - k * 0.5, w - k * 0.7, 0), resample=Image.BICUBIC, fillcolor=200)
    return img.resize((1275, 1650))

def main():
    out = ROOT / "data" / "scans"; out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in (ROOT / "data" / "emails.jsonl").open()]
    for r in rows:
        rnd = random.Random(r["doc_id"])
        degrade(render(r, rnd), rnd).save(out / f"{r['doc_id']}.jpg", quality=rnd.randint(45, 75))
    print("rendered", len(rows))

if __name__ == "__main__":
    main()
