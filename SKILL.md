---
name: clinic-funnel
description: "Build a branded phone-funnel prototype for one med spa or clinic from its Instagram: photo service tiles, matched real before/afters, 3 questions, contact, result, demo phone-consult calendar. Trigger on \"build a funnel for <clinic or @handle>\", \"phone funnel for <client>\", \"clinic funnel\", or /clinic-funnel."
---

# Clinic phone funnel

One shared template, one `funnel.json` per client. The look (soft, rounded, dimensional, readable type) and the flow are fixed in `template.html`; per client you only gather real assets and fill the config.

- `KIT` = this skill's folder (normally `~/.claude/skills/clinic-funnel`). Every command below is `python3 $KIT/<script>.py`.
- Client folders live in `campaigns/` under the user's current project. One folder per client; build.py compares sibling folders to block cross-client leaks.
- `$KIT/studio.json` holds the builder name shown as "Prototype by …" on every page. If it still says "Your Studio", ask the user for their studio name once and save it there.

Flow the page gives you: provider card + photo tiles → that service's real before/afters → how big a change → timing → treated before → contact (first name + mobile, email optional) → analyzing → personal result + real reviews → demo phone-consult calendar in the clinic's real hours → confirmation. The "Prototype by … · demo calendar, nothing is booked" banner is fixed in the template.

## Laws (build.py enforces most of them and refuses to build)
1. **Only real patient photos the clinic already posted publicly.** Never AI-generate, edit or fake a result or a face. Every before/after carries its source post URL. Consent for funnel use is "confirm with clinic" unless the user says otherwise.
2. **Front page = only services with a real photo.** A service with no photo goes in `others` (shown under "Something else" with a what-to-expect card), never as a placeholder tile.
3. **Every claim is sourced** from the clinic's IG captions, site or posts: no invented stats, reviews, ratings or results. No prices unless confirmed (`"prices_sourced": true`).
4. **Provider photo** = a professional headshot from the clinic's website team/about page. Only if none exists, the most professional IG photo of them (not a selfie, candid or treatment shot). Note the source URL.
5. **One client per folder.** A funnel uses only its own folder's photos, words and reviews. Never reuse another client's before/afters, provider photo, reviews or captions.
6. **Prototype only.** No network calls, no pixel, no real form submission, nothing booked. Don't touch ad accounts or CRMs. Don't commit or push unless asked.

## Steps
Say one line to the user at each step boundary.

1. **Folder.** `campaigns/<client>-funnel-<mmdd>/`. If there's a `BRIEF.md`, read it; its rules win over this file's defaults.
2. **Profile + site.** Apify `apify/instagram-scraper` with `resultsType: "details"` → bio, link in bio. Follow the link (Linktree etc.) to the website and read its services menu, team page, about/footer (address, hours).
3. **Posts.** Apify `apify/instagram-scraper`, `resultsType: "posts"`, `resultsLimit: 200` (start with `waitSecs: 0`, poll `get-actor-run`). Then:
   `python3 $KIT/assets.py download <dir> <datasetId>`
   No Apify connector? Ask the user to add it (or to drop the clinic's before/after images into `<dir>/assets/raw/` named `<n>_<shortcode>_1.jpg`) and continue from step 4.
4. **Find the before/afters.** `assets.py find <dir>` (or a regex like `'lip|filler'`), then `assets.py sheet <dir> <idx> ...` and **look at the sheet** (Read tool). Tag each real before/after to a service. Copy each keeper with `assets.py pick <dir> <service> <raw file>`; it prints the `[file, caption, source]` triple for `funnel.json`. Write the caption from the post (what was treated, sessions, amounts), not from imagination.
5. **Provider photo.** Download the team-page headshot into `assets/provider/`, crop to head-and-shoulders without altering the face, save into `assets/picks/provider/`.
6. **Brand.** From the IG grid and site: ground (page background), ink (text), action (button colour), accent; a Google Fonts text face (sturdy, readable at 16px, e.g. Jost, Manrope, DM Sans, Figtree) and the wordmark font or a logo image. build.py derives the rest and fails if text contrast is too low.
7. **Config.** Write `<dir>/funnel.json` fresh from the schema in `$KIT/README.md`. `$KIT/examples/acme-funnel/funnel.json` shows the shape; never copy another client's text, questions or reviews. Questions are optional (generic defaults exist); write client-specific notes only from sourced facts.
8. **Build.** `python3 $KIT/build.py <dir>`. Fix every problem it lists. It writes the page and `funnel/sources.md`.
9. **Check once.** `python3 $KIT/check.py <dir> --out <dir>/.check`, open `.check/check.jpg`, fix what you see, rebuild. One pass, no loops. (Needs Playwright + Google Chrome; skip with a note if missing.)
10. **Share.** If an Artifact tool is available, publish the built HTML (icon `calendar`, one-sentence description) and revise by republishing the **same file path** so the link stays. Otherwise give the user the file path to open in a browser.
11. **README.md** in the client folder: services found → tiles vs "Something else", asset counts (`assets.py catalog <dir>`), paste `funnel/sources.md` (every before/after + source + consent flag, provider photo source, reviews), open questions for the clinic, share link.

## Handing it to the client
Register the client in `$KIT/clients.json` first (slug → folder, names, optional `blocked` names), and confirm before/after consent.
- No-install package for their Drive folder: `python3 $KIT/package.py <dir>` → `~/client-packages/<Clinic> Funnel/` (START HERE editor, finished page, how-to, photo sources).
- Their own repo: `python3 $KIT/export.py <dir>` → `~/client-repos/<slug>-funnel` (git, one commit, no remote).
Both scan every file for other clients' names and the `internal_words` in `studio.json`, and stop on any hit.

## Changing the look for everyone
Edit `$KIT/template.html` (or `derive_theme` in `build.py`), then rebuild each client folder that should pick it up and check one. Don't fork the template per client; if a client truly needs something different, add a config option.
