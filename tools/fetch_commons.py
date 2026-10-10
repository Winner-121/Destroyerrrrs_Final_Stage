"""Download licensed truck photos from Wikimedia Commons and log each one in data/SOURCES.csv.

Only files with CC0 / CC BY / CC BY-SA / public-domain licences are kept. Attribution is recorded.
Usage: python tools/fetch_commons.py
"""
import csv, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SRC = ROOT / "data" / "SOURCES.csv"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "LoadSafetyGateBot/0.1 (hackathon research; mohamed@drivo.com)"}
ALLOWED = re.compile(r"^(CC0|CC BY|CC BY-SA|Public domain|PD)", re.I)

# (category, subset tag, max files, recurse into subcategories)
PLAN = [
    ("Automobile transport trucks", "car_carrier", 70, True),
    ("Overloaded vehicles", "overloaded", 60, True),
    ("Oversized loads", "oversized", 30, False),
    ("Overweight loads", "oversized", 15, False),
    ("Flatbed rigid trucks", "flatbed", 20, False),
    ("Flatbed drawbar trucks", "flatbed", 15, False),
    ("Low loaders", "flatbed", 20, False),
    ("Semi-trailer trucks", "semi", 30, False),
    ("Trucks at night", "night", 40, True),
    ("Trucks in Baden-Württemberg at night", "night", 15, False),
]


def q(params):
    params.update({"format": "json"})
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 * (i + 1)); continue
            raise
        except Exception:
            time.sleep(3)
    return {}


def members(cat, recurse, limit):
    files, cats, cont = [], [], {}
    while len(files) < limit * 3:
        r = q({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat, "cmtype": "file|subcat", "cmlimit": 200, **cont})
        for m in r.get("query", {}).get("categorymembers", []):
            (cats if m["ns"] == 14 else files).append(m["title"])
        cont = r.get("continue", {})
        time.sleep(1.2)
        if not cont:
            break
    if recurse:
        for c in cats[:12]:
            if len(files) >= limit * 3:
                break
            files += members(c.replace("Category:", ""), False, limit)
    return files


def info(titles):
    r = q({"action": "query", "prop": "imageinfo", "titles": "|".join(titles), "iiprop": "url|mime|extmetadata|size", "iiurlwidth": 1280})
    out = []
    for p in r.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [None])[0]
        if not ii:
            continue
        em = ii.get("extmetadata", {})
        g = lambda k: html.unescape(re.sub("<[^>]+>", "", em.get(k, {}).get("value", ""))).strip()
        out.append({"title": p["title"], "mime": ii.get("mime"), "w": ii.get("width"), "h": ii.get("height"),
                    "thumb": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl"),
                    "licence": g("LicenseShortName"), "licence_url": g("LicenseUrl"), "author": g("Artist") or g("Credit")})
    return out


def main():
    done = set()
    if SRC.exists():
        with open(SRC) as f:
            done = {r["source_url"] for r in csv.DictReader(f)}
    rows = []
    for cat, subset, limit, recurse in PLAN:
        titles = [t for t in members(cat, recurse, limit)]
        kept = 0
        for i in range(0, len(titles), 25):
            if kept >= limit:
                break
            for it in info(titles[i:i + 25]):
                if kept >= limit:
                    break
                if it["mime"] not in ("image/jpeg", "image/png") or not it["w"] or it["w"] < 600:
                    continue
                if not ALLOWED.match(it["licence"] or ""):
                    continue
                if it["page"] in done:
                    continue
                name = subset + "_" + re.sub(r"[^A-Za-z0-9]+", "_", it["title"].replace("File:", ""))[:60].strip("_") + ".jpg"
                dest = RAW / subset; dest.mkdir(parents=True, exist_ok=True)
                try:
                    req = urllib.request.Request(it["thumb"], headers=UA)
                    (dest / name).write_bytes(urllib.request.urlopen(req, timeout=60).read())
                except Exception as e:
                    print("skip", name, e, file=sys.stderr); continue
                rows.append({"filename": name, "source_url": it["page"], "dataset_or_site": "Wikimedia Commons / " + cat,
                             "licence": it["licence"] + (" " + it["licence_url"] if it["licence_url"] else ""),
                             "attribution": it["author"], "subset": subset, "notes": ""})
                done.add(it["page"]); kept += 1
                time.sleep(0.6)
            time.sleep(1.2)
        print(f"{cat}: kept {kept}", flush=True)
    new = not SRC.exists() or SRC.stat().st_size < 120
    with open(SRC, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "source_url", "dataset_or_site", "licence", "attribution", "subset", "notes"])
        if new and f.tell() == 0:
            w.writeheader()
        w.writerows(rows)
    print("total new", len(rows))


if __name__ == "__main__":
    main()
