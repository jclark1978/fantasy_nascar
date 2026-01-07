#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


URL = "https://www.nascar.com/standings/nascar-cup-series/"
OUTFILE = "nascar_cup_standings.json"


def clean_header(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    s = s.replace("\n", " ")
    return s


def df_to_records(df: pd.DataFrame):
    # Normalize column names
    df.columns = [clean_header(c) for c in df.columns]
    # Strip whitespace in string cells
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).map(lambda x: x.strip())
    return df.to_dict(orient="records")


def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)

        # Give the site a moment to render the tables
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()
        return html


def parse_as_of_text(soup: BeautifulSoup) -> str | None:
    # On this page there is usually a line like:
    # "After Phoenix - November 2nd, 2025 - Race 36 of 36"
    text = soup.get_text("\n", strip=True)
    m = re.search(r"After\s+.+?\s+-\s+.+?\s+-\s+Race\s+\d+\s+of\s+\d+", text)
    return m.group(0) if m else None


def main():
    html = fetch_rendered_html(URL)

    soup = BeautifulSoup(html, "html.parser")
    as_of = parse_as_of_text(soup)

    # Extract ALL HTML tables on the page
    # (driver standings, owner standings, manufacturer standings, and small summary tables)
    dfs = pd.read_html(html)

    tables = []
    for i, df in enumerate(dfs):
        # Drop completely empty columns/rows
        df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")

        # Skip tiny/empty tables that sometimes appear
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

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(tables)} tables -> {OUTFILE}")
    if as_of:
        print(f"Detected: {as_of}")


if __name__ == "__main__":
    main()
