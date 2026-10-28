#!/usr/bin/env python3
"""Build a client phone funnel from <client_dir>/funnel.json + photos.

    python3 funnel-kit/build.py campaigns/<client>-funnel-<mmdd>

Reads funnel.json, validates it (fails fast with a list of problems), derives the full palette from
four brand colours, resizes and inlines every photo, fills template.html and writes:
  - the page (funnel.json "output", default funnel/funnel.html)
  - funnel/sources.md: every image, provider photo and review with its source, for the README
"""
import base64
import html
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

try:  # optional: smaller pages. Without it, macOS 'sips' shrinks photos; elsewhere photos go in as-is.
    from PIL import Image
except ImportError:
    Image = None

KIT = pathlib.Path(__file__).resolve().parent
TEMPLATE = KIT / "template.html"
MAX_BYTES = 15_000_000
PHOTO_BOX = (760, 960)
PROVIDER_BOX = (600, 750)
JPEG_Q = 74
FALLBACK_TEXT = '"Avenir Next","Helvetica Neue",Arial,sans-serif'
FALLBACK_MARK = 'Georgia,"Times New Roman",serif'
STUDIO_FILE = KIT / "studio.json"


def studio():
    """Kit-wide settings: who builds these funnels (shown on every page) and extra words exports must never ship."""
    s = json.loads(STUDIO_FILE.read_text()) if STUDIO_FILE.is_file() else {}
    return {"name": s.get("name") or "Your Studio", "internal_words": s.get("internal_words") or []}


class ConfigError(Exception):
    pass


# ---------- colour ----------
def hex_rgb(h):
    h = h.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ConfigError(f"not a 6-digit hex colour: #{h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return "#" + "".join(f"{round(v):02X}" for v in c)


def mix(a, b, t):
    """Mix colour a toward b by t (0..1)."""
    ra, rb = hex_rgb(a), hex_rgb(b)
    return rgb_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def luminance(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def derive_theme(t):
    """Four brand colours in, every token the template uses out."""
    g, ink, act, acc = t["ground"], t["ink"], t["action"], t["accent"]
    on_act = t.get("on_action") or mix(g, "#FFFFFF", 0.3)
    tok = {
        "ground": g, "surface": mix(g, "#FFFFFF", 0.62), "white": mix("#FFFFFF", g, 0.15),
        "step": mix(g, ink, 0.045), "step-2": mix(g, ink, 0.10),
        "ink": ink, "ink-2": mix(ink, g, 0.18),
        "action": act, "action-press": mix(act, "#000000", 0.45), "on-action": on_act,
        "action-2": mix(act, on_act, 0.10), "on-action-2": mix(on_act, act, 0.18), "on-action-3": mix(on_act, act, 0.42),
        "accent": acc, "wash-1": mix(g, acc, 0.28), "wash-2": mix(g, acc, 0.16),
        "err": "#9A3A26", "err-bg": "#F4E1DA",
    }
    problems = []
    if contrast(ink, g) < 7:
        problems.append(f"theme: ink {ink} on ground {g} is {contrast(ink, g):.1f}:1, needs 7:1 for running text")
    if contrast(on_act, act) < 4.5:
        problems.append(f"theme: button text {on_act} on action {act} is {contrast(on_act, act):.1f}:1, needs 4.5:1")
    return tok, problems


def theme_css(tok, text_font, mark_font):
    sr = ",".join(str(v) for v in hex_rgb(tok["action"]))
    lines = [f"  --{k}:{v};" for k, v in tok.items()]
    lines += [
        f"  --ground-rgb:{','.join(str(v) for v in hex_rgb(tok['ground']))}; --accent-rgb:{','.join(str(v) for v in hex_rgb(tok['accent']))}; --shadow-rgb:{sr};",
        f"  --sh-1:0 1px 2px rgba({sr},.06),0 10px 30px rgba({sr},.12);",
        f"  --sh-2:0 2px 4px rgba({sr},.08),0 18px 44px rgba({sr},.20);",
        f"  --sh-btn:0 1px 2px rgba({sr},.10),0 10px 24px rgba({sr},.26);",
        "  --r-tile:22px; --r-card:24px; --r-big:28px; --r-inp:16px;",
        f'  --mark:"{mark_font}",{FALLBACK_MARK};',
        f'  --sans:"{text_font}",{FALLBACK_TEXT};',
        "  --ease:cubic-bezier(.16,1,.3,1);",
        "  color-scheme:light;",
    ]
    return ":root{\n" + "\n".join(lines) + "\n}\n"


def fonts_url(text_font, mark_font, mark_weight):
    fam = lambda f: f.replace(" ", "+")
    parts = [f"family={fam(text_font)}:wght@400..700"]
    if mark_font and mark_font != text_font:
        parts.append(f"family={fam(mark_font)}:wght@{mark_weight}")
    return "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"


# ---------- images ----------
WEB_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
BIG_PHOTO = 1_500_000


def shrink(path, box):
    """Photo -> (bytes, mime), fitted inside box. Pillow if installed, else macOS sips, else the file as-is."""
    path = pathlib.Path(path)
    if Image is not None:
        im = Image.open(path).convert("RGB")
        im.thumbnail(box)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
        return buf.getvalue(), "image/jpeg"
    if shutil.which("sips"):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "photo.jpg"
            subprocess.run(["sips", "-Z", str(max(box)), "-s", "format", "jpeg", "-s", "formatOptions", str(JPEG_Q),
                            str(path), "--out", str(out)], check=True, capture_output=True)
            return out.read_bytes(), "image/jpeg"
    mime = WEB_TYPES.get(path.suffix.lower())
    if not mime:
        raise ConfigError(f"{path.name}: save it as JPG or PNG first (or run: python3 -m pip install pillow)")
    data = path.read_bytes()
    if len(data) > BIG_PHOTO:
        print(f"note: {path.name} is {len(data) / 1e6:.1f} MB; 'python3 -m pip install pillow' makes pages much smaller", file=sys.stderr)
    return data, mime


def data_uri(path, box):
    data, mime = shrink(path, box)
    return f"data:{mime};base64," + base64.b64encode(data).decode()


# ---------- validation ----------
REQUIRED = {
    "clinic": ["name", "short"],
    "theme": ["ground", "ink", "action", "accent", "text_font"],
    "provider": ["name", "short", "role", "photo", "photo_source"],
    "consult": ["label"],
    "copy": ["headline", "subhead"],
}
PRICE = re.compile(r"\$\s?\d")


def other_clinic_names(client):
    """Names of every other client that has a funnel.json in campaigns/, to block cross-client leaks."""
    names = set()
    for f in client.parent.glob("*/funnel.json"):
        if f.parent == client:
            continue
        try:
            cl = json.loads(f.read_text()).get("clinic", {})
        except json.JSONDecodeError:
            continue
        names |= {n for n in (cl.get("name"), cl.get("short")) if n}
    return names


def validate(cfg, assets):
    p = []
    root = assets.resolve()
    for f in [img[0] for s in cfg.get("services", []) for img in s.get("imgs", []) if img] + [cfg.get("provider", {}).get("photo") or ""]:
        if f and root not in (assets / f).resolve().parents:
            p.append(f"image {f} is outside this client's assets/ folder; every photo must belong to this client")
    for sect, keys in REQUIRED.items():
        for k in keys:
            if not (cfg.get(sect) or {}).get(k):
                p.append(f"{sect}.{k} is required")
    if not cfg.get("services"):
        p.append("services: at least one service with a real photo is required")
    for s in cfg.get("services", []):
        sid = s.get("id", "?")
        for k in ("id", "name", "plan", "body"):
            if not s.get(k):
                p.append(f"services[{sid}].{k} is required")
        if not s.get("imgs"):
            p.append(f"services[{sid}]: front-page tiles need a real photo; move it to 'others' if there is none")
        for img in s.get("imgs", []):
            if len(img) < 3 or not all(img[:3]):
                p.append(f"services[{sid}]: each image is [file, caption, source_url]")
            elif "<" in img[1] or ">" in img[1]:
                p.append(f"services[{sid}]: write a real caption for {img[0]} (it still says {img[1]})")
            elif not (assets / img[0]).is_file():
                p.append(f"services[{sid}]: missing file assets/{img[0]}")
    for o in cfg.get("others", []):
        if not o.get("expect"):
            p.append(f"others[{o.get('id', '?')}]: needs an 'expect' list of [label, text]")
    for r in cfg.get("reviews", []):
        if not (r.get("quote") and r.get("name") and r.get("source")):
            p.append("reviews: each review needs quote, name and source (no invented reviews)")
    hours = cfg.get("hours") or {}
    if not hours:
        p.append("hours: needed for the demo calendar, e.g. {\"2\": [10, 18]} (0=Sun)")
    for d, oc in hours.items():
        if d not in list("0123456") or len(oc) != 2 or not 0 <= oc[0] < oc[1] <= 24:
            p.append(f"hours[{d}]: use weekday 0-6 -> [open, close] in 24h")
    if cfg.get("provider", {}).get("photo") and not (assets / cfg["provider"]["photo"]).is_file():
        p.append(f"provider.photo: missing file assets/{cfg['provider']['photo']}")
    if not cfg.get("prices_sourced"):
        text = json.dumps({k: v for k, v in cfg.items() if k not in ("theme",)})
        if PRICE.search(text):
            p.append("copy contains a price; remove it or set \"prices_sourced\": true after confirming it with the clinic")
    return p


# ---------- build ----------
def build(client_dir):
    client = pathlib.Path(client_dir).resolve()
    cfg_path = client / "funnel.json"
    if not cfg_path.is_file():
        raise ConfigError(f"no funnel.json in {client}")
    cfg = json.loads(cfg_path.read_text())
    assets = client / "assets"
    problems = validate(cfg, assets)
    own = {cfg.get("clinic", {}).get("name", ""), cfg.get("clinic", {}).get("short", "")}
    text = json.dumps(cfg, ensure_ascii=False).lower()
    for other in sorted(other_clinic_names(client) - own):
        if other.lower() in text:
            problems.append(f"funnel.json mentions another client ({other}); copied text from their config?")
    tok, theme_problems = derive_theme(cfg["theme"]) if not problems else ({}, [])
    problems += theme_problems
    if problems:
        raise ConfigError("\n".join(f"  - {x}" for x in problems))

    th, pv, cl = cfg["theme"], cfg["provider"], cfg["clinic"]
    wm = cfg.get("wordmark") or {"text": cl["short"], "font": th["text_font"], "weight": 600}
    mark_font, mark_weight = wm.get("font", th["text_font"]), wm.get("weight", 600)
    if wm.get("image"):
        wordmark = f'<img class="mark" src="{data_uri(assets / wm["image"], (400, 120))}" alt="{html.escape(cl["name"])}" style="height:32px;width:auto">'
    else:
        wordmark = f'<div class="mark" aria-label="{html.escape(cl["name"])}">{html.escape(wm["text"])}</div>'

    runtime = {k: cfg[k] for k in ("clinic", "provider", "consult", "copy", "hours", "others", "questions", "reviews") if k in cfg}
    runtime["services"] = [{**s, "imgs": [[data_uri(assets / f, PHOTO_BOX), cap] for f, cap, *_ in s["imgs"]]} for s in cfg["services"]]

    e = html.escape
    fills = {
        "TITLE": e(cfg.get("title") or f"{cl['short']} Consult Finder"),
        "FONTS_URL": fonts_url(th["text_font"], mark_font, mark_weight),
        "THEME_CSS": theme_css(tok, th["text_font"], mark_font),
        "WORDMARK": wordmark,
        "PROVIDER_IMG": data_uri(assets / pv["photo"], PROVIDER_BOX),
        "CLINIC": e(cl["name"]), "CLINIC_SHORT": e(cl["short"]),
        "BUILDER": e(cfg.get("builder") or studio()["name"]),
        "ADDRESS_SEP": e(", " + cl["address"]) if cl.get("address") else "",
        "CONSULT": e(cfg["consult"]["label"]),
        "HEADLINE": e(cfg["copy"]["headline"]), "SUBHEAD": e(cfg["copy"]["subhead"]),
        "P_NAME": e(pv["name"]), "P_SHORT": e(pv["short"]), "P_ROLE": e(pv["role"]),
        "P_NAME_CRED": e(f"{pv['name']}, {pv['credentials']}" if pv.get("credentials") else pv["name"]),
        "P_ROLE_LONG": e(pv.get("role_long") or pv["role"]),
        "P_ROLE_SHORT": e(pv.get("role_short") or pv["role"]),
        "PHONE_PLACEHOLDER": e(cfg.get("phone_placeholder", "305 555 0123")),
        "CFG": json.dumps(runtime, ensure_ascii=False).replace("</", "<\\/"),
    }
    out = TEMPLATE.read_text()
    for k, v in fills.items():
        out = out.replace("{{" + k + "}}", v)
    out = re.sub(r"<!--.*?-->", "", out, flags=re.S)  # ship no comments: they are visible in page source
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise ConfigError(f"template placeholders not filled: {sorted(set(left))}")
    if len(out.encode()) > MAX_BYTES:
        raise ConfigError(f"page is {len(out.encode()) / 1e6:.1f} MB; artifacts allow 16 MB. Use fewer or smaller photos.")

    dest = client / cfg.get("output", "funnel/funnel.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)
    (dest.parent / "sources.md").write_text(sources_md(cfg))
    n = sum(len(s["imgs"]) for s in cfg["services"])
    print(f"built {dest.relative_to(client)}  ({len(out.encode()) / 1e6:.2f} MB, {len(cfg['services'])} photo tiles, {n} before/afters, {len(cfg.get('others', []))} under 'Something else')")


def sources_md(cfg):
    rows = ["| Service | File | Caption | Source post | Consent |", "|---|---|---|---|---|"]
    for s in cfg["services"]:
        for f, cap, src, *rest in s["imgs"]:
            consent = rest[0] if rest else "confirm with clinic"
            rows.append(f"| {s['name']} | `{f}` | {cap} | {src} | {consent} |")
    pv = cfg["provider"]
    out = ["# Sources (generated by funnel-kit/build.py, do not edit)", "", "## Before/afters used", *rows, "",
           "## Provider photo", f"- {pv['name']}: `{pv['photo']}` from {pv['photo_source']}", ""]
    if cfg.get("reviews"):
        out += ["## Reviews quoted", *[f"- {r['name']}: \"{r['quote']}\" ({r['source']})" for r in cfg["reviews"]], ""]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        build(sys.argv[1])
    except ConfigError as err:
        sys.exit(f"funnel.json problems:\n{err}")
