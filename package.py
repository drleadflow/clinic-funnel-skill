#!/usr/bin/env python3
"""Make a no-install client package (for their Google Drive folder) from one client funnel folder.

    python3 funnel-kit/package.py campaigns/<client>-funnel-<mmdd> [--dest ~/client-packages]

Writes "<Clinic> Funnel/" with:
  START HERE.html            double-click: their funnel on a phone + a 6-step editor (kit clients)
                             or a preview with how to ask for changes (folders built before the kit)
  Your funnel (ready).html   the finished page as it is today
  How to use.txt             plain steps
  Photo sources.txt          every before/after and where it came from (kit clients)
Everything is self-contained (photos inlined); nothing to install. The same other-client and
internal-notes scan as export.py runs before anything is written.
"""
import argparse
import html
import json
import pathlib
import shutil
import sys
import tempfile

KIT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import build  # noqa: E402
import export  # noqa: E402

PHOTO_BOX, PROVIDER_BOX = build.PHOTO_BOX, build.PROVIDER_BOX
INTERNAL_KEYS = ("output", "hours_source")


def js_literal(obj):
    """JSON that is safe inside a <script> block."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def packaged_config(client, cfg):
    """The client's config with every photo inlined, so the editor needs no other files."""
    assets = client / "assets"
    out = {k: v for k, v in cfg.items() if k not in INTERNAL_KEYS}
    out["services"] = [{**s, "imgs": [[build.data_uri(assets / f, PHOTO_BOX), cap, src] for f, cap, src, *_ in s["imgs"]]}
                       for s in cfg["services"]]
    out["provider"] = {**cfg["provider"], "photo": build.data_uri(assets / cfg["provider"]["photo"], PROVIDER_BOX)}
    if cfg.get("wordmark", {}).get("image"):
        out["wordmark"] = {**cfg["wordmark"], "image": build.data_uri(assets / cfg["wordmark"]["image"], (400, 120))}
    return out


def how_to(name, editable):
    steps = [
        f"{name} funnel",
        "",
        "1. Double-click \"START HERE.html\". It opens in your web browser (Chrome, Safari or Edge).",
        "   If it opens in another app, right-click it and choose Open With > Google Chrome.",
    ]
    if editable:
        steps += [
            "2. On the right is your funnel on a phone. Tap through it like a patient would.",
            "3. On the left, press Next to go through the steps: your details, colours, treatments and photos, reviews.",
            "   Type over anything; the phone updates as you type. Your changes save on this computer automatically.",
            f"4. On the last step, press \"Download my funnel\". Send that file to {export.BUILDER} to put live,",
            "   or paste it into a custom code block in your page builder.",
            "",
            "Moving to another computer? On the last step press \"Save my settings file\", then on the other computer",
            "open START HERE and press \"Open a settings file\".",
        ]
    else:
        steps += [
            "2. Tap through your funnel on the phone like a patient would.",
            f"3. Want changes? Write them down (what to change, which screen) and send them to {export.BUILDER}.",
        ]
    steps += [
        "",
        "\"Your funnel (ready).html\" is the finished page as it is today.",
        "This is a prototype: the calendar is a demo, nothing is booked and the form sends nothing anywhere.",
        "Internet is only needed for the fonts; everything else works offline.",
    ]
    return "\n".join(steps) + "\n"


def viewer(name, page_html):
    """START HERE for folders built before the kit: preview only, plus how to ask for changes."""
    e = html.escape
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)} funnel: start here</title>
<style>body{{margin:0;background:#F4F1EC;color:#1F1A17;font:17px/1.55 "Avenir Next","Segoe UI",Helvetica,Arial,sans-serif}}
.wrap{{display:grid;grid-template-columns:minmax(320px,440px) auto;gap:40px;justify-content:center;align-items:center;min-height:100vh;padding:24px}}
@media (max-width:820px){{.wrap{{grid-template-columns:1fr}}}}
h1{{font-size:28px;line-height:1.2;margin:0 0 12px}} ol{{padding-left:22px}} li{{margin-bottom:10px}}
.tip{{background:#ECE7E0;border-radius:16px;padding:14px 16px;margin-top:18px}}
.phone{{width:390px;max-width:100%;height:min(820px,calc(100vh - 48px));border-radius:44px;background:#111;padding:12px;box-shadow:0 30px 70px rgba(0,0,0,.25)}}
iframe{{width:100%;height:100%;border:0;border-radius:34px;background:#fff}}</style></head><body>
<div class="wrap"><div><p style="font-weight:700;color:#5A4F47;margin:0 0 4px">Your funnel, by {e(export.BUILDER)}</p><h1>{e(name)} funnel</h1>
<ol><li>The phone shows your funnel. Tap through it like a patient would.</li>
<li>Note anything you'd like changed: the words, a photo, your hours, colours.</li>
<li>Send your notes to {e(export.BUILDER)} and we'll update it.</li></ol>
<div class="tip">This is a prototype. The calendar is a demo, nothing is booked and the form sends nothing anywhere.</div></div>
<div class="phone"><iframe id="p" title="Your funnel on a phone"></iframe></div></div>
<script>document.getElementById("p").srcdoc = {js_literal(page_html)};</script></body></html>"""


def package(client_dir, dest_root):
    client = pathlib.Path(client_dir).resolve()
    slug, entry = export.client_entry(client)
    name = entry["names"][0]
    stage = pathlib.Path(tempfile.mkdtemp(prefix=f"package-{slug}-"))
    cfg_file = client / "funnel.json"
    if cfg_file.exists():
        cfg = json.loads(cfg_file.read_text())
        build.build(client)
        page = client / cfg.get("output", "funnel/funnel.html")
        editor = (KIT / "editor.html").read_text()
        fills = {"__CLINIC__": html.escape(name), "__TEMPLATE__": js_literal((KIT / "template.html").read_text()),
                 "__CONFIG__": js_literal(packaged_config(client, cfg)), "__BUILDER__": html.escape(export.BUILDER)}
        for k, v in fills.items():
            editor = editor.replace(k, v)
        (stage / "START HERE.html").write_text(editor)
        rows = [f"{s['name']}: {cap} ({src})" for s in cfg["services"] for _, cap, src, *_ in s["imgs"]]
        (stage / "Photo sources.txt").write_text(
            "Every before/after in your funnel is from your public Instagram. Please confirm you're happy for each to be used.\n\n"
            + "\n".join(rows) + f"\n\nProvider photo: {cfg['provider']['photo_source']}\n")
        editable = True
    else:
        page = client / entry["page"]
        editable = False
    export.ship_page(page, stage / "Your funnel (ready).html")
    if not editable:
        (stage / "START HERE.html").write_text(viewer(name, (stage / "Your funnel (ready).html").read_text()))
    (stage / "How to use.txt").write_text(how_to(name, editable))

    hits = export.scan(stage, slug)
    if hits:
        shutil.rmtree(stage)
        raise export.ExportError("stopped, found other-client or internal text:\n" + "\n".join(f"  - {h}" for h in hits[:40]))
    dest = pathlib.Path(dest_root).expanduser() / f"{name} Funnel"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(stage), dest)
    size = sum(f.stat().st_size for f in dest.iterdir()) / 1e6
    print(f"{slug}: {'editor' if editable else 'preview'} package -> {dest}  ({size:.1f} MB, scan clean)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client_dir")
    ap.add_argument("--dest", default="~/client-packages")
    a = ap.parse_args()
    try:
        package(a.client_dir, a.dest)
    except (export.ExportError, build.ConfigError) as err:
        sys.exit(str(err))
