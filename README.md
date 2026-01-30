# Incept

Incept is a small CLI for turning course outlines into a structured course payload, inserting that payload into your database (currently Notion), and (optionally) preparing a Jellyfin-friendly video folder hierarchy and downloading lesson videos (Rebelway).

This README is written for the “I’m adding a new course” workflow.

---

## What you’ll run most often

1) **Build the payload JSON** from `chapters.csv` + `lessons.csv`
2) **Add the course** to Notion (optionally create Jellyfin folders + artwork)
3) **Download the videos** from Rebelway (from `lessons.xlsx`)

---

## Install / first-time setup

### 1) Initialize user config (~/.incept)

```bash
incept init
```

This creates:

- `~/.incept/.env` (copied from `env.example` if missing)
- `~/.incept/templates/`
- `~/.incept/payload/`
- `~/.incept/mapping/`

### 2) Configure your `.env`

Edit:

```bash
nano ~/.incept/.env
```

At minimum you usually want:

- `DATABASE_NAME=notion`
- `NOTION_API_KEY=...`
- `NOTION_COURSE_DATABASE_ID=...`

(Your code will also accept `--api-key` / `--database-id` overrides, but most of the time `.env` is easiest.)

---

## Workflow: add a new course

### Step 0: Prepare inputs

You generally need:

- `chapters.csv` — course chapter list
- `lessons.csv` — lesson list with `chapter_index`
- **For downloading videos:** `lessons.xlsx` (sheet: `lessons`) with columns:
  - `chapter_index`
  - `name`
  - `link`

> Note: the downloader currently reads **Excel**, not CSV.

---

## 1) Build the payload JSON

Command:

```bash
incept build-payload \
  --course-name "Coding Generative AI" \
  --course-desc "..." \
  --intro-link "https://rebelway.academy/lessons/welcome-83/" \
  --chapters ~/.incept/payload/chapters.csv \
  --lessons  ~/.incept/payload/lessons.csv \
  --chapter-name-template "Week {i:02d}" \
  --tool 166a1865-b187-8138-8316-dc8288897458 \
  --tool 149a1865-b187-80f9-b21f-c9c96430bf62 \
  --instructor "Felipe Pesantez" \
  --tags Houdini \
  --tags Python \
  --template default \
  --thumb-base-public-id "thumb/base_image" \
  --out ~/.incept/payload/coding_gen_ai.json
```

Notes:

- `--tool`, `--instructor`, `--tags` are **repeatable** flags.
- `--range 2-4` will build only those chapters (useful for testing).
- `--chapter-name-template "Week {i:02d}"` formats the chapter names from chapter index.

---

## 2) Add the course (insert into Notion)

### 2a) Insert course (no Jellyfin folders/artwork)

```bash
incept add-course --data-file-path ~/.incept/payload/coding_gen_ai.json
```

### 2b) Insert + create Jellyfin video folder hierarchy (+ artwork)

```bash
incept add-course --data-file-path ~/.incept/payload/coding_gen_ai.json --include-video
```

What `--include-video` does (high level):

- Creates a Jellyfin-friendly folder structure
- Generates artwork (poster/thumb/logo/background)
- Stores the full episode paths in Notion (so Jellyfin + filesystem match)

---

## 3) Download all lesson videos (Rebelway)

This is driven by **Excel** (`lessons.xlsx`), not your CSV payload.

```bash
incept dl-rebelway \
  --excel  ~/.incept/mapping/lessons.xlsx \
  --output ~/Videos/rebelway/coding_gen_ai \
  --chrome-port 9222
```

Options:

- Skip initial rows (if your sheet has headers or you want to resume):

```bash
incept dl-rebelway --excel ~/.incept/mapping/lessons.xlsx --output ~/Videos/rebelway/coding_gen_ai --skip-first 10
```

- Download only one chapter (week):

```bash
incept dl-rebelway --excel ~/.incept/mapping/lessons.xlsx --output ~/Videos/rebelway/coding_gen_ai --range 3
```

- Download a chapter range:

```bash
incept dl-rebelway --excel ~/.incept/mapping/lessons.xlsx --output ~/Videos/rebelway/coding_gen_ai --range 2-4
```

### How the downloader works (important)

- It launches Chrome with remote debugging (`--chrome-port`, default 9222)
- You log in manually, then hit ENTER in the terminal
- Selenium reads each lesson page and extracts the “SOURCE” MP4 from the download selector
- A requests session reuses your Chrome cookies and downloads the file

---

## Troubleshooting

### Font error when using `--include-video`

If you see:

```
OSError: cannot open resource
```

It means Pillow can’t open one of the font files used for artwork generation.

Your code currently loads fonts from a **package-relative path**:

```
<incept package dir>/.config/fonts/coresansc/
```

Common causes:

- Fonts folder is missing (not included in install)
- Filenames don’t match what the code expects:
  - `coresansc35.otf`
  - `coresansc75.otf`
  - `coresansc25.otf`

Quick checks:

```bash
python -c "import incept.asset_generator as a; from pathlib import Path; p=Path(a.__file__).parent/'.config/fonts/coresansc'; print('FONT_DIR=', p); print('exists=', p.exists()); print([x.name for x in p.glob('*')])"
```

Temporary workaround:

- Run without `--include-video` to insert the course first:

```bash
incept add-course --data-file-path ~/.incept/payload/coding_gen_ai.json
```

Recommended long-term fix (implementation idea):

- Move fonts to `~/.incept/fonts/coresansc` and load from there, or
- Package fonts as data files and load via `importlib.resources`

---

### “Downloader doesn’t find SOURCE”

If you get warnings like “No SOURCE found”, generate a report:

```bash
incept report-broken \
  --excel  ~/.incept/mapping/lessons.xlsx \
  --output ~/.incept/mapping/broken_sources.csv \
  --chrome-port 9222
```

---

## Quick reference (cheat sheet)

### Build payload
```bash
incept build-payload --course-name "..." --course-desc "..." --intro-link "..." --chapters chapters.csv --lessons lessons.csv --out payload.json
```

### Insert course
```bash
incept add-course --data-file-path payload.json
```

### Insert course + Jellyfin folders
```bash
incept add-course --data-file-path payload.json --include-video
```

### Download videos (Rebelway)
```bash
incept dl-rebelway --excel lessons.xlsx --output /path/to/videos
```

---

## Repo layout (high level)

```
src/incept/cli.py             # click CLI entry points
src/incept/payload.py         # payload building (CSV → nested JSON)
src/incept/courses.py         # DB insert logic (courses/chapters/lessons)
src/incept/utils.py           # folder creation + helper utilities
src/incept/asset_generator.py # Jellyfin artwork generation
src/incept/dl_rebelway.py     # Rebelway lesson page parsing + download loop
src/incept/dl_video.py        # Chrome remote debug + cookies + streaming download
```

