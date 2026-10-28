---
name: clinic-funnel
description: "Build a branded phone-funnel prototype for one med spa or clinic from photos the clinic sends or from its public Instagram: photo service tiles, matched real before/afters, 3 questions, contact, result, demo phone-consult calendar. Trigger on \"build a funnel for <clinic or @handle>\", \"phone funnel for <client>\", \"clinic funnel\", or /clinic-funnel."
---

# Clinic phone funnel

One shared template, one `funnel.json` per client. The look (soft, rounded, dimensional, readable type) and the flow are fixed in `template.html`; per client you only gather real assets and fill the config.

- `KIT` = this skill's folder (normally `~/.claude/skills/clinic-funnel`). Every command below is `python3 $KIT/<script>.py`.
- Client folders live in `campaigns/` under the user's current project. One folder per client; build.py compares sibling folders to block cross-client leaks.
- `$KIT/studio.json` holds the builder name shown as "Prototype by …" on every page. If it still says "Your Studio", ask the user for their studio name once and save it there.

Flow the page gives you: provider card + photo tiles → that service's real before/afters → how big a change → timing → treated before → contact (first name + mobile, email optional) → analyzing → personal result + real reviews → demo phone-consult calendar in the clinic's real hours → confirmation. The "Prototype by … · demo calendar, nothing is booked" banner is fixed in the template.

## Laws (build.py enforces most of them and refuses to build)
1. **Only real patient photos**, either sent by the clinic or already posted publicly by it. Never AI-generate, edit or fake a result or a face. Every before/after records where it came from (post URL, or "provided by the clinic"). Consent for funnel use is "confirm with clinic" unless the user says otherwise.
2. **Front page = only services with a real photo.** A service with no photo goes in `others` (shown under "Something else" with a what-to-expect card), never as a placeholder tile.
3. **Every claim is sourced** from the clinic's IG captions, site or posts: no invented stats, reviews, ratings or results. No prices unless confirmed (`"prices_sourced": true`).
4. **Provider photo** = a professional headshot from the clinic's website team/about page. Only if none exists, the most professional IG photo of them (not a selfie, candid or treatment shot). Note the source URL.
5. **One client per folder.** A funnel uses only its own folder's photos, words and reviews. Never reuse another client's before/afters, provider photo, reviews or captions.
6. **Prototype only.** No network calls, no pixel, no real form submission, nothing booked. Don't touch ad accounts or CRMs. Don't commit or push unless asked.

## Steps
Say one line to the user at each step boundary. Use plain words: the user may not be technical.

0. **Ready check.** `python3 --version` must work. If not, tell the user exactly: Mac: run `xcode-select --install`, or install Python 3 from python.org; then try again. Nothing else needs installing. Pillow and Playwright are optional extras.
1. **Ask how to get the before/afters** (skip if the user already said). Ask once, explaining both routes like this:
   > I need real before/after photos of this clinic's patients. Two ways:
   > **A. You send them.** I make a folder with one sub-folder per treatment. You (or the clinic) drop the photos in, and optionally one line per photo saying what was treated. Best when the clinic has good photos that aren't on social, or you want full control.
   > **B. I pull them from the clinic's public Instagram.** I use the Apify connector in Claude to read the clinic's public posts (about 200, nothing gets posted or liked), download the images to this computer, and look for posts whose captions say before/after or results. I show you a contact sheet, and you approve each photo I want to use. Every photo keeps a link to its original post. This needs the Apify connector turned on in Claude (Settings → Connectors); Apify's free credit covers it.
   > Either way: only real, unedited photos the clinic has already shared, and the clinic should OK their use before this goes live.
   If they pick B but Apify isn't connected, say how to connect it, or offer route A.
2. **Folder.** `campaigns/<client>-funnel-<mmdd>/` under the current folder. If there's a `BRIEF.md`, read it; its rules win over this file's defaults.
3. **Clinic facts.** From the clinic's website (and Instagram bio if route B): services menu, team/about page (provider name, credentials, headshot), address, hours, brand colours and fonts. Ask the user for anything you can't find. Never guess hours, prices or credentials.
4. **Photos.**
   - **Route A:** `python3 $KIT/assets.py inbox <dir> <service> [service...]` (one per treatment, e.g. `lip-filler botox morpheus8`). Tell the user the printed folder path and wait for "photos are in". Then `python3 $KIT/assets.py import <dir>`; it copies them into `assets/picks/` and prints the `imgs` rows. Look at each imported photo (Read tool). Any caption still `<what was treated: ...>` gets asked of the user; build.py refuses placeholders.
   - **Route B:** Apify `apify/instagram-scraper`, `resultsType: "posts"`, `resultsLimit: 200`, `directUrls: ["https://www.instagram.com/<handle>/"]` (start with `waitSecs: 0`, poll `get-actor-run`). Then `python3 $KIT/assets.py download <dir> <datasetId>`, `assets.py find <dir>` (or a regex like `'lip|filler'`), `assets.py sheet <dir> <idx> ...` and **look at the sheet** (Read tool). Show the user your picks and get a yes before using them. Copy each keeper with `assets.py pick <dir> <service> <raw file>`; it prints the `[file, caption, source]` row. Write the caption from the post (what was treated, sessions, amounts), not from imagination.
5. **Provider photo.** A headshot from the clinic's website team/about page (or one the user sends) into `assets/picks/provider/`. Crop to head-and-shoulders without altering the face. Note where it came from.
6. **Brand.** ground (page background), ink (text), action (button colour), accent; a Google Fonts text face (sturdy, readable at 16px, e.g. Jost, Manrope, DM Sans, Figtree) and a wordmark font or logo image. build.py derives the rest and fails if text contrast is too low.
7. **Config.** Write `<dir>/funnel.json` fresh from the schema in `$KIT/README.md`. `$KIT/examples/acme-funnel/funnel.json` shows the shape; never copy another client's text, questions or reviews. Questions are optional (generic defaults exist). Reviews only word for word from a real source.
8. **Build.** `python3 $KIT/build.py <dir>`. Fix every problem it lists and rebuild.
9. **Look once.** `python3 $KIT/check.py <dir> --out <dir>/.check`; if it ran, open `.check/check.jpg` and fix what you see. If it says "skipped", open the built page yourself (Read tool) and check the copy. One pass, no loops.
10. **Share.** If an Artifact tool is available, publish the built HTML (icon `calendar`, one-sentence description) and revise by republishing the **same file path** so the link stays. Otherwise tell the user the file path and to double-click it.
11. **README.md** in the client folder: services → tiles vs "Something else", paste `funnel/sources.md` (every photo + where it came from + consent flag, provider photo source, reviews), open questions for the clinic, share link.

## Handing it to the client
Register the client in `$KIT/clients.json` first (slug → folder, names, optional `blocked` names), and confirm before/after consent.
- No-install package for their Drive folder: `python3 $KIT/package.py <dir>` → `~/client-packages/<Clinic> Funnel/` (START HERE editor, finished page, how-to, photo sources).
- Their own repo: `python3 $KIT/export.py <dir>` → `~/client-repos/<slug>-funnel` (git, one commit, no remote).
Both scan every file for other clients' names and the `internal_words` in `studio.json`, and stop on any hit.

## Changing the look for everyone
Edit `$KIT/template.html` (or `derive_theme` in `build.py`), then rebuild each client folder that should pick it up and check one. Don't fork the template per client; if a client truly needs something different, add a config option.
