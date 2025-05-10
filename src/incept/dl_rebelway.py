# src/incept/dl_rebelway.py
import os
import html
import re
import pandas as pd

from urllib.parse                import urlsplit
from bs4                         import BeautifulSoup
from selenium.common.exceptions import InvalidSessionIdException

from .dl_video import (
    launch_chrome,
    make_chrome_driver,
    make_download_session,
    download_stream,
)

def find_source_url(html_text: str) -> str | None:
    """Return the VIDEO SOURCE URL from Rebelway’s download <select>, or None."""
    soup = BeautifulSoup(html_text, "html.parser")
    sel  = soup.select_one("select.video-download-selector")
    if not sel:
        return None
    for opt in sel.find_all("option"):
        if "source" in opt.get_text(strip=True).lower():
            return html.unescape(opt["value"])
    return None

def download_rebelway(
    excel_path: str,
    out_dir:    str,
    skip_first: int = 0,
    chrome_port:int = 9222,
    chapter_range: tuple[int,int] | None = None,
) -> None:
    """
    Read the 'lessons' sheet of the Excel file, 
    launch Chrome & Selenium, then download every SOURCE MP4.
    """
    # 1) Kick off Chrome & wait for you to log in
    launch_chrome(debug_port=chrome_port)

    # 2) Read Excel
    df = pd.read_excel(excel_path, sheet_name="lessons", engine="openpyxl")
    if not {"chapter_index","name","link"}.issubset(df.columns):
        raise ValueError("Excel must have columns: chapter_index, name, link")


    # 2a) filter to the requested chapter(s)
    if chapter_range:
        start, end = chapter_range
        df = df[df["chapter_index"].between(start, end)]
        if df.empty:
            print(f"⚠️  No rows found for chapter range {start}-{end}; exiting.")
            return

    # 3) Prepare Selenium + requests
    driver = make_chrome_driver(debug_port=chrome_port)
    sess   = make_download_session()
    os.makedirs(out_dir, exist_ok=True)

    # 4) Seed episode counters
    ep = {}
    for row in df.iloc[:skip_first].itertuples():
        c = int(row.chapter_index)
        ep[c] = ep.get(c, 0) + 1

    # 5) Loop & download
    for idx, row in df.iterrows():
        if idx < skip_first:
            continue

        chap   = int(row["chapter_index"])
        title  = str(row["name"])
        lesson = row["link"]

        # increment count for this chapter, even on broken
        ep.setdefault(chap, 0)
        ep[chap] += 1
        season, episode = chap, ep[chap]

        # generate slug
        slug = "".join(
            ch.lower() if ch.isalnum() or ch.isspace() else "_" 
            for ch in title
        ).strip().replace(" ", "_")

        print(f"\n➡️  [{idx+1}] {lesson} → s{season:02d}e{episode:02d}_{slug}.mp4")

        # load page (restart on session death)
        try:
            driver.get(lesson)
        except InvalidSessionIdException:
            driver.quit()
            driver = make_chrome_driver(debug_port=chrome_port)
            driver.get(lesson)

        driver.implicitly_wait(3)
        html_body = driver.page_source
        src_url   = find_source_url(html_body)
        if not src_url:
            print(f"⚠️  No SOURCE found for s{season:02d}e{episode:02d}")
            continue

        ext   = os.path.splitext(urlsplit(src_url).path)[1] or ".mp4"
        fname = f"s{season:02d}e{episode:02d}_{slug}{ext}"
        dest  = os.path.join(out_dir, fname)

        if os.path.exists(dest):
            print(f"⏭  Already downloaded: {fname}")
            continue

        # Vimeo needs Referer
        sess.headers["Referer"] = lesson
        print(f"↓ Downloading: {fname}")
        try:
            download_stream(sess, src_url, dest)
            print(f"✔  Saved → {dest}")
        except Exception as e:
            print(f"❌  Failed → {e}")

    driver.quit()
    print("\n🎉 All done.")

def report_broken_sources(
    excel_path: str,
    out_csv:    str,
    chrome_port:int = 9222
):
    """
    Scan every lesson for a missing SOURCE option.
    Write rows (with chapter_index, name, link) to out_csv.
    """
    launch_chrome(debug_port=chrome_port)

    df = pd.read_excel(excel_path, sheet_name="lessons", engine="openpyxl")
    if not {"chapter_index","name","link"}.issubset(df.columns):
        raise ValueError("Excel must have columns: chapter_index, name, link")

    driver = make_chrome_driver(debug_port=chrome_port)
    broken = []

    for idx, row in df.iterrows():
        url = row.link
        try:
            driver.get(url)
        except InvalidSessionIdException:
            driver.quit()
            driver = make_chrome_driver(debug_port=chrome_port)
            driver.get(url)
        driver.implicitly_wait(3)

        if not find_source_url(driver.page_source):
            broken.append({
                "row": idx+2,
                "chapter_index": row.chapter_index,
                "name": row.name,
                "link": row.link
            })
            print(f"❌ Row {idx+2}: No SOURCE → {url}")

    driver.quit()

    pd.DataFrame(broken).to_csv(out_csv, index=False)
    print(f"\n✅ Wrote {len(broken)} broken entries to {out_csv}")
