#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def load_slugs(roster_path: Path) -> list[str]:
    data = json.loads(roster_path.read_text(encoding="utf-8"))
    slugs = []
    for driver in data.get("drivers", []):
        slug = driver.get("driver_slug")
        if slug:
            slugs.append(slug)
    return slugs


def fetch_profile_html(slug: str) -> str:
    url = f"https://www.nascar.com/drivers/{slug}"
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
        try:
            page.wait_for_selector(".ndms2023-driver-hero-left-col img", timeout=20_000)
        except Exception:
            pass
        html = page.content()
        browser.close()
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch NASCAR driver profile HTML pages.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--roster", default="", help="Path to normalized roster JSON")
    parser.add_argument("--out-dir", default="data/raw/driver_profiles")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of profiles fetched")
    parser.add_argument("--slugs", default="", help="Comma-separated list of slugs to fetch")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    roster_path = Path(args.roster) if args.roster else base_dir / "data/normalized" / f"roster_{args.season}.json"
    out_dir = base_dir / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.slugs:
        slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    else:
        slugs = load_slugs(roster_path)

    if args.limit and args.limit > 0:
        slugs = slugs[: args.limit]

    for slug in slugs:
        html = fetch_profile_html(slug)
        (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"Wrote {out_dir / f'{slug}.html'}")
        if args.sleep:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
