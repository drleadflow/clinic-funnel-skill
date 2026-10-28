#!/usr/bin/env python3
"""Instagram asset helper for a client funnel folder.

    python3 funnel-kit/assets.py download <client_dir> <dataset_id>   # Apify posts dataset -> assets/raw/
    python3 funnel-kit/assets.py find     <client_dir> [regex]         # list image posts whose caption matches
    python3 funnel-kit/assets.py sheet    <client_dir> <idx> [idx...]  # contact sheet of those posts, to look at
    python3 funnel-kit/assets.py pick     <client_dir> <service> <raw file>  # copy into assets/picks/<service>/
    python3 funnel-kit/assets.py catalog  <client_dir>                 # write assets/catalog.csv

Raw files are named <post index>_<shortCode>_<child|v>.jpg. assets/raw/ must stay out of git.
"""
import concurrent.futures as cf
import csv
import json
import pathlib
import re
import sys
import urllib.request

from PIL import Image, ImageDraw

APIFY_ITEMS = "https://api.apify.com/v2/datasets/{}/items?format=json&clean=1"
UA = {"User-Agent": "Mozilla/5.0"}
BA_WORDS = re.compile(r"before ?\+? ?(and|&|\+)? ?after|transformation|results? (shown|speak)", re.I)
DEFAULT_FIND = r"before|after|result|transformation|treated|provider:"
PICK_BOX = (760, 960)


def paths(client):
    c = pathlib.Path(client).resolve()
    return c, c / "assets" / "raw", c / "assets" / "raw" / "posts.json"


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    dest.write_bytes(urllib.request.urlopen(req, timeout=30).read())


def ensure_gitignore(client):
    gi = client / ".gitignore"
    lines = gi.read_text().splitlines() if gi.exists() else []
    for need in ("assets/raw/", ".check/"):
        if need not in lines:
            lines.append(need)
    gi.write_text("\n".join(lines) + "\n")


def download(client, dataset_id):
    c, raw, pj = paths(client)
    raw.mkdir(parents=True, exist_ok=True)
    ensure_gitignore(c)
    fetch(APIFY_ITEMS.format(dataset_id), pj)
    posts = json.loads(pj.read_text())
    jobs = []
    for i, p in enumerate(posts):
        kids = p.get("childPosts") or []
        if kids:
            jobs += [(f"{i:03d}_{p['shortCode']}_{k}.jpg", ch["displayUrl"]) for k, ch in enumerate(kids) if ch.get("displayUrl")]
        elif p.get("displayUrl"):
            jobs.append((f"{i:03d}_{p['shortCode']}_{'v' if p.get('type') == 'Video' else 0}.jpg", p["displayUrl"]))

    def get(job):
        name, url = job
        dest = raw / name
        if dest.exists():
            return True
        try:
            fetch(url, dest)
            return True
        except Exception as err:  # report and continue; one dead CDN link should not stop the batch
            print(f"  failed {name}: {err}", file=sys.stderr)
            return False

    with cf.ThreadPoolExecutor(16) as ex:
        ok = sum(ex.map(get, jobs))
    print(f"{len(posts)} posts, {ok}/{len(jobs)} images in {raw.relative_to(c)}")


def find(client, pattern=DEFAULT_FIND):
    _, _, pj = paths(client)
    rx = re.compile(pattern, re.I)
    for i, p in enumerate(json.loads(pj.read_text())):
        cap = (p.get("caption") or "").replace("\n", " ")
        if p.get("type") != "Video" and rx.search(cap):
            print(f"{i:3d} {p['shortCode']} kids={len(p.get('childPosts') or [])} | {cap[:180]}")


def sheet(client, idxs, w=260, cols=6):
    c, raw, _ = paths(client)
    files = [f for i in idxs for f in sorted(raw.glob(f"{int(i):03d}_*.jpg"))]
    if not files:
        sys.exit("no raw files for those indexes")
    rows = (len(files) + cols - 1) // cols
    im = Image.new("RGB", (cols * w, rows * (w + 18)), "white")
    dr = ImageDraw.Draw(im)
    for n, f in enumerate(files):
        t = Image.open(f).convert("RGB")
        t.thumbnail((w, w))
        x, y = (n % cols) * w, (n // cols) * (w + 18)
        im.paste(t, (x, y))
        dr.text((x + 3, y + w + 3), f.name[:26], fill="black")
    out = c / ".check" / "sheet.jpg"
    out.parent.mkdir(exist_ok=True)
    im.save(out, quality=80)
    print(out)


def pick(client, service, raw_name):
    c, raw, pj = paths(client)
    src = raw / raw_name
    if not src.is_file():
        sys.exit(f"no such raw file: {raw_name}")
    dest = c / "assets" / "picks" / service / raw_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    im.thumbnail(PICK_BOX)
    im.save(dest, quality=80, optimize=True)
    posts = json.loads(pj.read_text())
    url = posts[int(raw_name[:3])]["url"]
    print(json.dumps([f"picks/{service}/{raw_name}", "<caption from the post>", url]))


def catalog(client):
    c, raw, pj = paths(client)
    posts = json.loads(pj.read_text())
    used = {}
    cfg_file = c / "funnel.json"
    if cfg_file.exists():
        for s in json.loads(cfg_file.read_text()).get("services", []):
            for f, *_ in s["imgs"]:
                used[pathlib.Path(f).name] = s["id"]
    rows = []
    for f in sorted(raw.glob("*.jpg")):
        p = posts[int(f.name[:3])]
        cap = p.get("caption") or ""
        rows.append({"url": p["url"], "file": f.name, "type": "video_thumb" if f.stem.endswith("_v") else "image",
                     "caption": cap[:300].replace("\n", " "), "likes": p.get("likesCount"), "date": (p.get("timestamp") or "")[:10],
                     "service_tag": used.get(f.name, ""), "is_before_after": "yes" if f.name in used or BA_WORDS.search(cap) else "no",
                     "notes": "USED IN FUNNEL" if f.name in used else ""})
    out = c / "assets" / "catalog.csv"
    with out.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"{out.relative_to(c)}: {len(rows)} rows, {sum(r['is_before_after'] == 'yes' for r in rows)} before/after, {len(used)} used")


if __name__ == "__main__":
    a = sys.argv[1:]
    cmds = {"download": (download, 3), "find": (find, 2), "sheet": (sheet, 3), "pick": (pick, 4), "catalog": (catalog, 2)}
    if not a or a[0] not in cmds or len(a) < cmds[a[0]][1]:
        sys.exit(__doc__)
    fn = cmds[a[0]][0]
    if a[0] == "sheet":
        fn(a[1], a[2:])
    else:
        fn(*a[1:])
