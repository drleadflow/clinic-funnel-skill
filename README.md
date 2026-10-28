# clinic-funnel: a Claude Code skill for med spa phone funnels

Point Claude at a clinic's Instagram and get a branded, phone-first funnel prototype: photo service tiles, the clinic's own real before/afters, three short questions, contact capture, a personal result with real reviews, and a demo phone-consult calendar in the clinic's actual hours. One shared template, one `funnel.json` per clinic.

It is a **prototype builder**: the page makes no network calls, sends no form data and books nothing. Use it to win the client and agree the funnel, then build the live version in your CRM.

## Install (2 minutes)

**Easiest:** open Claude Code and paste:

```
Install the clinic-funnel skill: clone https://github.com/drleadflow/clinic-funnel-skill into ~/.claude/skills/clinic-funnel
```

**Or in a terminal (Mac/Linux):**

```bash
git clone https://github.com/drleadflow/clinic-funnel-skill.git ~/clinic-funnel-skill
~/clinic-funnel-skill/install.sh
```

**Windows:** download the ZIP from GitHub (green Code button → Download ZIP), unzip it, and put the folder at `C:\Users\<you>\.claude\skills\clinic-funnel`.

### What you need
- **Claude Code**
- **Python 3**: already on most Macs. If Claude says it's missing: Mac `xcode-select --install`, or python.org.

That's it. Nothing to `pip install`. Optional extras, only if you want them:
- `python3 -m pip install pillow`: smaller pages on Windows/Linux (Macs shrink photos without it)
- `python3 -m pip install playwright` + Google Chrome: an automatic screenshot check of every screen
- **Apify connector** in Claude (Settings → Connectors): only for photo route B below

## Use it

Open Claude Code in any folder and say **"build a funnel for @clinichandle"** (or `/clinic-funnel`). Claude asks you one question first, where the before/after photos come from:

| | A. You send the photos | B. Pull from the clinic's Instagram |
|---|---|---|
| How | Claude makes a `photos/` folder with one sub-folder per treatment (`lip-filler/`, `botox/`…). You drop the clinic's before/afters in and say "photos are in". | Claude uses the Apify connector to read the clinic's ~200 most recent **public** posts, downloads the images to your computer, finds the before/after posts by their captions and shows you a contact sheet. You approve each photo. |
| Captions | Optional `captions.txt` per folder: `photo.jpg \| 1 syringe, upper lip`. Claude asks for any that are missing. | Written from each post's own caption. |
| Source recorded | "provided by the clinic" | the post's link |
| Needs | nothing | the Apify connector (free credit covers it) |
| Best when | the clinic has photos that aren't on social, or you want full control | the clinic posts results regularly |

Nothing is ever posted, liked or sent anywhere. Either way the funnel uses only real, unedited patient photos, and the clinic should OK their use before it goes live.

Then Claude reads the clinic's website for services, provider, hours and brand colours, writes `funnel.json`, builds one self-contained HTML page, and gives you a link or a file to open on your phone.

## Try the example first

```bash
cd ~/.claude/skills/clinic-funnel
python3 build.py examples/acme-funnel
open examples/acme-funnel/funnel/funnel.html     # Windows: start, Linux: xdg-open
```

The example uses grey sample photos. Real funnels use only real before/afters.

| File | What it does |
|---|---|
| `SKILL.md` | The skill Claude follows: laws and steps. |
| `template.html` | The page. Soft rounded cards, layered brand-tinted shadows, 16px+ readable type. Don't edit per client. |
| `build.py` | `funnel.json` + photos → one self-contained HTML page and `funnel/sources.md`. Validates first. |
| `check.py` | Clicks through every screen at 375px, saves screenshots and a contact sheet, reports script errors and overflow. |
| `assets.py` | Photo helper. Route A: `inbox`, `import`. Route B: `download`, `find`, `sheet`, `pick`, `catalog`. |
| `package.py` | No-install package for the clinic: a START HERE page with a live 6-step editor. |
| `export.py` | The clinic's own editable repo. |
| `studio.json` | Your studio name and any words that must never ship to a client. |
| `clients.json` | Your clients, so exports can block one client's name leaking into another's files. |

## Rules it enforces
- Only real photos, sent by the clinic or posted publicly by it, each with its source. No AI-generated or edited results.
- A service gets a front-page tile only if it has a real photo.
- No invented reviews, stats or prices (a `$` blocks the build until you confirm prices with the clinic).
- One client per folder; build and export stop if another client's name or photos show up.
- You are responsible for getting the clinic's OK to use their patient photos in a funnel. `sources.md` lists every photo with its source so they can approve each one.

## Quick start (by hand, without Claude)
```bash
KIT=~/.claude/skills/clinic-funnel
# Route A: the clinic's own photos
python3 $KIT/assets.py inbox  campaigns/acme-funnel-1101 lip-filler botox
#   ...drop photos into campaigns/acme-funnel-1101/photos/<treatment>/
python3 $KIT/assets.py import campaigns/acme-funnel-1101          # prints the "imgs" rows for funnel.json
# Route B: public Instagram (Apify posts dataset id)
python3 $KIT/assets.py download campaigns/acme-funnel-1101 <datasetId>
python3 $KIT/assets.py find  campaigns/acme-funnel-1101
python3 $KIT/assets.py sheet campaigns/acme-funnel-1101 12 17 21
python3 $KIT/assets.py pick  campaigns/acme-funnel-1101 lips 017_DdG1uo9m8Vb_1.jpg
# then write campaigns/acme-funnel-1101/funnel.json from the schema below and build
python3 $KIT/build.py campaigns/acme-funnel-1101
python3 $KIT/check.py campaigns/acme-funnel-1101 --out campaigns/acme-funnel-1101/.check   # optional
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
