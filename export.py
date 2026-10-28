#!/usr/bin/env python3
"""Export one client's funnel into its own standalone repo folder, safe to hand to that client.

    python3 funnel-kit/export.py <client_dir> [--dest ~/client-repos] [--no-git]

Two modes:
  kit     the folder has funnel.json: ships funnel.json, only the photos it uses, the built page,
          sources.md and a client copy of the kit, so the client can edit and rebuild.
  page    no funnel.json (built before the kit): ships only the finished page. Its scripts and photo
          folders are left behind on purpose: they reach into other campaign folders and hold unused
          or unapproved photos. Port the folder to the kit to make it editable.

Before anything is written for real, every text file is scanned for other clients' names and internal
notes; any hit stops the export. HTML comments are stripped from shipped pages.
"""
import argparse
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

KIT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import build  # noqa: E402

CLIENTS = json.loads((KIT / "clients.json").read_text()) if (KIT / "clients.json").is_file() else {}
BUILDER = build.studio()["name"]
KIT_FILES_FOR_CLIENT = ["template.html", "build.py", "check.py", "assets.py"]
# Internal words that must never reach a client repo.
INTERNAL = ["phase 2", "upsell", "internal note", "TODO"] + build.studio()["internal_words"]
DATA_URI = re.compile(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+")
COMMENT = re.compile(r"<!--.*?-->", re.S)
TEXT_EXT = {".html", ".json", ".md", ".py", ".txt", ".csv", ".gitignore"}


class ExportError(Exception):
    pass


def client_entry(client):
    for slug, c in CLIENTS.items():
        if c["folder"] and c["folder"] == client.name:
            return slug, c
    raise ExportError(f"{client.name} is not in funnel-kit/clients.json; add it (slug, folder, names, page) first")


BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"^[ \t]*//[^\n]*\n", re.M)
STYLE_OR_SCRIPT = re.compile(r"(<(style|script)\b[^>]*>)(.*?)(</\2>)", re.S | re.I)


def strip_code_comments(m):
    body = BLOCK_COMMENT.sub("", m.group(3))
    if m.group(2).lower() == "script":
        body = LINE_COMMENT.sub("", body)
    return m.group(1) + body + m.group(4)


def ship_page(src, dest):
    """Ship a page without any notes: HTML comments, CSS comments, script block and whole-line comments."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    html = COMMENT.sub("", src.read_text())
    dest.write_text(STYLE_OR_SCRIPT.sub(strip_code_comments, html))


def export_kit(client, cfg, stage):
    (stage / "funnel-kit").mkdir()
    for f in KIT_FILES_FOR_CLIENT:
        shutil.copy2(KIT / f, stage / "funnel-kit" / f)
    (stage / "funnel-kit" / "studio.json").write_text(json.dumps({"name": BUILDER}, indent=2) + "\n")  # name only, never internal_words
    used = [img[0] for s in cfg["services"] for img in s["imgs"]] + [cfg["provider"]["photo"]]
    if cfg.get("wordmark", {}).get("image"):
        used.append(cfg["wordmark"]["image"])
    for rel in used:
        src = client / "assets" / rel
        dst = stage / "assets" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copy2(client / "funnel.json", stage / "funnel.json")
    out = cfg.get("output", "funnel/funnel.html")
    ship_page(client / out, stage / out)
    if (client / "funnel" / "sources.md").exists():
        shutil.copy2(client / "funnel" / "sources.md", stage / "funnel" / "sources.md")
    return out, len(used)


def export_page(client, entry, stage):
    src = client / entry["page"]
    if not src.is_file():
        raise ExportError(f"built page not found: {src}")
    out = f"funnel/{src.name}"
    ship_page(src, stage / out)
    return out, 0


def readme(entry, mode, page, artifact):
    name = entry["names"][0]
    lines = [f"# {name} funnel", "",
             f"Your phone funnel prototype, built by {BUILDER}. Open `{page}` in a browser to try it on a phone-sized window.",
             "", "It is a prototype: the calendar is a demo, nothing is booked, and the form sends nothing anywhere.", ""]
    if artifact:
        lines += [f"Live preview: {artifact}", ""]
    if mode == "kit":
        lines += ["## Change it", "",
                  "Everything on the page comes from `funnel.json` (services, photos, provider, hours, questions, reviews, colours).",
                  "Photos live in `assets/`. After editing:", "", "```bash",
                  "pip install pillow            # once",
                  "python3 funnel-kit/build.py .",
                  "```", "",
                  "Optional screen check (needs `pip install playwright` and Google Chrome): `python3 funnel-kit/check.py . --out .check`", "",
                  "## Photos", "",
                  "Every before/after shown is from your public Instagram; `funnel/sources.md` lists each one with its post link.",
                  "Please confirm you are happy for each to be used in a funnel.", ""]
    else:
        lines += ["## Change it", "",
                  f"This version is the finished page only. Ask {BUILDER} for changes, or for the editable version",
                  "(a `funnel.json` you can edit and rebuild yourself).", ""]
    return "\n".join(lines)


def scan(stage, slug):
    others = {n for s, c in CLIENTS.items() if s != slug for n in c["names"]} | set(CLIENTS[slug].get("blocked", []))
    hits = []
    for f in stage.rglob("*"):
        if not f.is_file() or ".git" in f.parts or (f.suffix not in TEXT_EXT and f.name != ".gitignore"):
            continue
        text = DATA_URI.sub("", f.read_text(errors="ignore"))
        for word in sorted(others) + INTERNAL:
            for m in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", text, re.I):
                ctx = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                hits.append(f"{f.relative_to(stage)}: '{m.group(0)}' … {ctx}")
    return hits


def export(client_dir, dest_root, use_git):
    client = pathlib.Path(client_dir).resolve()
    slug, entry = client_entry(client)
    cfg_file = client / "funnel.json"
    stage = pathlib.Path(tempfile.mkdtemp(prefix=f"export-{slug}-"))
    if cfg_file.exists():
        mode = "kit"
        cfg = json.loads(cfg_file.read_text())
        subprocess.run([sys.executable, str(KIT / "build.py"), str(client)], check=True)
        page, n = export_kit(client, cfg, stage)
    else:
        mode = "page"
        page, n = export_page(client, entry, stage)
    (stage / "README.md").write_text(readme(entry, mode, page, None))
    (stage / ".gitignore").write_text("assets/raw/\n.check/\n__pycache__/\n")

    hits = scan(stage, slug)
    if hits:
        shutil.rmtree(stage)
        raise ExportError("stopped, found other-client or internal text:\n" + "\n".join(f"  - {h}" for h in hits[:40]))

    dest = pathlib.Path(dest_root).expanduser() / f"{slug}-funnel"
    keep_git = dest / ".git"
    if dest.exists():
        for child in dest.iterdir():
            if child != keep_git:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    for child in stage.iterdir():
        shutil.move(str(child), dest / child.name)
    shutil.rmtree(stage)

    if use_git:
        if not keep_git.exists():
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dest, check=True)
        subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dest).returncode:
            msg = f"feat: {entry['names'][0]} funnel export {datetime.date.today().isoformat()}"
            subprocess.run(["git", "commit", "-q", "-m", msg], cwd=dest, check=True)
    files = sum(1 for f in dest.rglob("*") if f.is_file() and ".git" not in f.parts)
    print(f"{slug}: {mode} export -> {dest}  ({files} files, {n} photos, scan clean)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client_dir")
    ap.add_argument("--dest", default="~/client-repos")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    try:
        export(a.client_dir, a.dest, not a.no_git)
    except ExportError as err:
        sys.exit(str(err))
