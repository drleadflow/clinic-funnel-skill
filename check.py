#!/usr/bin/env python3
"""One 375 px check of a built funnel: clicks through every screen, saves screenshots and one contact sheet.

    python3 funnel-kit/check.py campaigns/<client>-funnel-<mmdd> [--out DIR]

Needs Playwright for Python and Google Chrome. Prints script errors and horizontal overflow;
open the contact sheet (DIR/check.jpg) and look at it before publishing.
"""
import argparse
import json
import pathlib
import sys
import tempfile

try:
    from PIL import Image
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Screen check skipped: it is optional and needs 'python3 -m pip install pillow playwright' plus Google Chrome.")
    print("Open the built funnel in your browser instead and tap through it at phone width.")
    sys.exit(0)

WIDTH, HEIGHT = 375, 812
SHEET_H = 1500
# The artifact host wraps the page in this skeleton; reproduce it so the check matches what viewers see.
SKELETON = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            'initial-scale=1,viewport-fit=cover"><style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}'
            '</style></head><body>{}</body></html>')


def run(client, out):
    cfg = json.loads((client / "funnel.json").read_text())
    page_file = client / cfg.get("output", "funnel/funnel.html")
    out.mkdir(parents=True, exist_ok=True)
    wrapped = out / "wrapped.html"
    wrapped.write_text(SKELETON.replace("{}", page_file.read_text()))
    shots, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        pg = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(wrapped.as_uri())
        pg.wait_for_timeout(1200)

        def shot(name, full=False):
            path = out / f"{name}.png"
            pg.screenshot(path=str(path), full_page=full)
            shots.append(path)

        shot("1-tiles")
        pg.click("#elseBtn")
        pg.wait_for_timeout(250)
        shot("1b-something-else", full=True)
        pg.click(".tile >> nth=0")
        pg.wait_for_timeout(900)
        shot("2-before-afters")
        pg.click('[data-step="2"] [data-next]')
        total = len(cfg.get("questions") or [0, 0, 0]) + 3
        for step in range(3, total):
            pg.wait_for_timeout(350)
            pg.click(f'[data-step="{step}"] .opt >> nth=0')
            pg.wait_for_timeout(250)
            if step == 3:
                shot("3-question")
            pg.click(f'[data-step="{step}"] [data-next]')
        pg.fill("#f-first", "Ana")
        pg.fill("#f-phone", "3055550123")
        pg.wait_for_timeout(500)
        shot("4-contact")
        pg.click("#form [type=submit]")
        pg.wait_for_timeout(3200)
        shot("5-result", full=True)
        pg.click(".slot >> nth=0")
        pg.click("#confirm")
        pg.wait_for_timeout(500)
        shot("6-confirmed")
        overflow = pg.evaluate("document.documentElement.scrollWidth") - WIDTH
        browser.close()

    ims = [Image.open(s).convert("RGB") for s in shots]
    ims = [i.crop((0, 0, WIDTH, min(i.height, SHEET_H))) for i in ims]
    sheet = Image.new("RGB", ((WIDTH + 10) * len(ims), SHEET_H), "white")
    for n, im in enumerate(ims):
        sheet.paste(im, (n * (WIDTH + 10), 0))
    sheet.save(out / "check.jpg", quality=80)
    print(f"contact sheet: {out / 'check.jpg'}")
    print(f"script errors: {errors or 'none'}")
    print(f"horizontal overflow: {overflow}px" if overflow > 0 else "horizontal overflow: none")
    return 1 if errors or overflow > 0 else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client_dir")
    ap.add_argument("--out", help="where screenshots go (default: a temp folder)")
    a = ap.parse_args()
    client = pathlib.Path(a.client_dir).resolve()
    out = pathlib.Path(a.out).resolve() if a.out else pathlib.Path(tempfile.mkdtemp(prefix="funnel-check-"))
    sys.exit(run(client, out))
