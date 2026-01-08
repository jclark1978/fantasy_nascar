#!/usr/bin/env python3
"""
driver_scraper.py

Scrapes NASCAR Cup Series standings page tables into a JSON file.

Why Playwright?
- nascar.com frequently blocks plain requests (403) and/or renders tables via JS.
- Playwright loads the page like a real browser, lets us dismiss cookie banners,
  waits for <table> elements, then we parse with pandas.

Output:
- nascar_cup_standings.json (by default)
- debug_page.html (only if no tables are found, to help troubleshoot)
"""

import json
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


URL = "https://www.nascar.com/standings/nascar-cup-series/"
BASE_DIR = Path(__file__).resolve().parents[1]
OUTFILE = BASE_DIR / "data/raw/nascar_cup_standings.json"
DEBUG_HTML = BASE_DIR / "data/raw/debug_page.html"


def clean_header(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s


def df_to_records(df: pd.DataFrame):
    df.columns = [clean_header(c) for c in df.columns]
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).map(lambda x: x.strip())
    return df.to_dict(orient="records")


def parse_as_of_text(soup: BeautifulSoup) -> str | None:
    """
    Attempts to find the "After <Race> - <Date> - Race X of Y" line.
    """
    text = soup.get_text("\n", strip=True)
    m = re.search(r"After\s+.+?\s+-\s+.+?\s+-\s+Race\s+\d+\s+of\s+\d+", text)
    return m.group(0) if m else None


def fetch_rendered_html(url: str) -> str:
    """
    Fetch fully rendered HTML via Playwright, try to dismiss cookie banner,
    then wait for tables to exist.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=90_000)

        # Try to dismiss cookie/consent UI if it shows up
        # NASCAR commonly uses OneTrust with buttons like these.
        for btn_name in ["Allow All", "Confirm My Choices", "Reject All"]:
            try:
                page.get_by_role("button", name=re.compile(btn_name, re.I)).click(timeout=3000)
                break
            except Exception:
                pass

        # Wait until at least one table is present
        page.wait_for_selector("table", timeout=30_000)

        html = page.content()
        browser.close()
        return html


def main():
    html = fetch_rendered_html(URL)

    soup = BeautifulSoup(html, "html.parser")
    as_of = parse_as_of_text(soup)

    # Extract all HTML tables on the page
    try:
        dfs = pd.read_html(StringIO(html))
    except ValueError:
        # No tables found: dump HTML for troubleshooting
        DEBUG_HTML.write_text(html, encoding="utf-8")
        raise ValueError(
            f"No tables found in rendered HTML. Wrote {DEBUG_HTML} for inspection."
        )

    tables = []
    for i, df in enumerate(dfs):
        df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
        if df.shape[0] == 0 or df.shape[1] == 0:
            continue

        tables.append(
            {
                "index": i,
                "shape": {"rows": int(df.shape[0]), "cols": int(df.shape[1])},
                "columns": [clean_header(c) for c in df.columns.tolist()],
                "rows": df_to_records(df),
            }
        )

    payload = {
        "source": URL,
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of,
        "tables": tables,
    }

    OUTFILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(tables)} tables -> {OUTFILE}")
    if as_of:
        print(f"Detected: {as_of}")


if __name__ == "__main__":
    main()
