# clinic-funnel: a Claude Code skill for med spa phone funnels

Point Claude at a clinic's Instagram and get a branded, phone-first funnel prototype: photo service tiles, the clinic's own real before/afters, three short questions, contact capture, a personal result with real reviews, and a demo phone-consult calendar in the clinic's actual hours. One shared template, one `funnel.json` per clinic.

It is a **prototype builder**: the page makes no network calls, sends no form data and books nothing. Use it to win the client and agree the funnel, then build the live version in your CRM.

## Install

```bash
git clone https://github.com/drleadflow/clinic-funnel-skill.git
cd clinic-funnel-skill && ./install.sh
```

The installer links the skill into `~/.claude/skills/clinic-funnel`, installs Pillow and Playwright for Python, and asks for your studio name (shown as "Prototype by …" on every funnel; stored in `studio.json`).

You also need:
- **Claude Code**
- **The Apify connector** in Claude, to pull the clinic's Instagram (`apify/instagram-scraper`). Without it, drop the clinic's images into `assets/raw/` yourself.
- **Google Chrome**, for the one-pass screen check (`check.py`)

Then in Claude Code: `build a funnel for @clinichandle` or `/clinic-funnel`.

## Try it in 30 seconds

```bash
python3 build.py examples/acme-funnel
open examples/acme-funnel/funnel/funnel.html     # Windows: start, Linux: xdg-open
```

The example uses grey sample photos. Real funnels use only real before/afters the clinic has already posted publicly.

| File | What it does |
|---|---|
| `SKILL.md` | The skill Claude follows: laws and steps. |
| `template.html` | The page. Soft rounded cards, layered brand-tinted shadows, 16px+ readable type. Don't edit per client. |
| `build.py` | `funnel.json` + photos → one self-contained HTML page and `funnel/sources.md`. Validates first. |
| `check.py` | Clicks through every screen at 375px, saves screenshots and a contact sheet, reports script errors and overflow. |
| `assets.py` | Instagram helper: `download`, `find`, `sheet`, `pick`, `catalog`. |
| `package.py` | No-install package for the clinic: a START HERE page with a live 6-step editor. |
| `export.py` | The clinic's own editable repo. |
| `studio.json` | Your studio name and any words that must never ship to a client. |
| `clients.json` | Your clients, so exports can block one client's name leaking into another's files. |

## Rules it enforces
- Only real photos the clinic posted publicly, each with its source post. No AI-generated or edited results.
- A service gets a front-page tile only if it has a real photo.
- No invented reviews, stats or prices (a `$` blocks the build until you confirm prices with the clinic).
- One client per folder; build and export stop if another client's name or photos show up.
- You are responsible for getting the clinic's OK to use their patient photos in a funnel. `sources.md` lists every photo with its source so they can approve each one.

## Quick start (by hand)
```bash
KIT=~/.claude/skills/clinic-funnel
python3 $KIT/assets.py download campaigns/acme-funnel-1101 <apify posts datasetId>
python3 $KIT/assets.py find  campaigns/acme-funnel-1101
python3 $KIT/assets.py sheet campaigns/acme-funnel-1101 12 17 21
python3 $KIT/assets.py pick  campaigns/acme-funnel-1101 lips 017_DdG1uo9m8Vb_1.jpg
# write campaigns/acme-funnel-1101/funnel.json from the schema below
python3 $KIT/build.py campaigns/acme-funnel-1101
python3 $KIT/check.py campaigns/acme-funnel-1101 --out campaigns/acme-funnel-1101/.check
```

## funnel.json
Image paths are relative to `<client>/assets/` and must stay inside it. `examples/acme-funnel/funnel.json` is a working example with sample photos; read it for the shape, never copy a real client's text.

```jsonc
{
  "title": "Acme Consult Finder",                 // tab + gallery name, 2-4 words
  "builder": "Your Studio",                       // optional; overrides studio.json for this client
  "output": "funnel/funnel.html",                 // optional; keep it fixed so republishing keeps the link
  "clinic":   { "name": "Acme Aesthetics", "short": "Acme", "address": "1 Main St, Miami" },
  "wordmark": { "text": "Acme", "font": "Bodoni Moda", "weight": 600 },   // or { "image": "brand/logo.png" }
  "theme": {                                      // four brand colours; everything else is derived
    "ground": "#EFEAE4", "ink": "#231A16", "action": "#2B211D", "accent": "#8A6A55",
    "on_action": "#F5F1EB",                       // optional button text colour
    "text_font": "Jost"                           // a Google Fonts family, sturdy at 16px
  },
  "provider": {
    "name": "Jane Doe", "short": "Jane", "credentials": "NP-C",
    "role": "Acme founder and nurse practitioner",          // "Your free phone consult is with Jane Doe, <role>."
    "role_short": "Founder, Acme Aesthetics", "role_long": "Founder, nurse practitioner, ...",
    "photo": "picks/provider/jane.jpg", "photo_source": "https://acme.com/team/"
  },
  "consult": { "label": "free phone consult" },
  "copy": { "headline": "What would you like to change?", "subhead": "Tap one to see real Acme results.",
            "unsure_body": "Most clients start with a conversation..." },
  "hours": { "2": [10, 18], "6": [9, 14] },       // weekday 0=Sun -> [open, close], 24h; demo slots stay inside
  "services": [                                   // front-page tiles; each needs at least one real photo
    { "id": "lips", "name": "Lip filler", "plan": "Your natural lip plan",
      "body": "One or two sourced sentences.",
      "imgs": [["picks/lips/017_x_1.jpg", "Caption from the post", "https://www.instagram.com/p/x/"]] }
  ],                                              // optional 4th item per image: consent note, e.g. "approved 11/02"
  "others": [                                     // no photo: listed under "Something else"
    { "id": "lhr", "name": "Laser hair removal", "plan": "Your laser hair removal plan", "body": "...",
      "expect": [["Sessions", "A series spaced weeks apart"]] }
  ],
  "questions": [ /* optional; omit for the generic 3. Each: key, label, head, why, opts: [value, label, note, phrase?] */ ],
  "reviews": [ { "quote": "...", "name": "Danelys", "source": "https://www.instagram.com/p/x/" } ],
  "prices_sourced": false                         // true only after the clinic confirms any $ in the copy
}
```

`{p}` and `{clinic}` in question text are replaced with the provider's short name and the clinic's short name.

## What build.py refuses
Missing required fields; a tile without a real photo; an image without a caption or source URL; a missing file; a review without a source; bad hours; text contrast under 7:1 (ink on ground) or 4.5:1 (button); a `$` price without `prices_sourced`; a page over 15 MB; any photo outside this client's `assets/`; any mention of another client that has a funnel.json. HTML comments are stripped from the built page.

## Hand a clinic their funnel
Register the clinic in `clients.json` first:
```json
{ "acme": { "folder": "acme-funnel-1101", "names": ["Acme Aesthetics", "Acme", "Jane Doe"], "blocked": [] } }
```
- **No-install package** (for their Google Drive): `python3 $KIT/package.py campaigns/acme-funnel-1101` → `~/client-packages/Acme Aesthetics Funnel/`. `START HERE.html` opens in a browser with their funnel on a phone plus a 6-step editor (details and hours, colours and fonts, treatments and photos, reviews), autosave, and "Download my funnel". Works offline except fonts.
- **Their own repo**: `python3 $KIT/export.py campaigns/acme-funnel-1101` → `~/client-repos/acme-funnel` (git, one commit, no remote).
- Both strip HTML/CSS/script comments and stop if any file names another client or holds a word from `studio.json` → `internal_words`.

## License
MIT
