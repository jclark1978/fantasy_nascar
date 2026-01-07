#!/usr/bin/env python3
"""
Fetch the NASCAR driver standings and render them to a simple HTML page.

Set RAPIDAPI_KEY (or NASCAR_API_KEY) to your RapidAPI key before running:
  RAPIDAPI_KEY=your_key python standings_report.py
"""

import html
import json
import os
import pathlib
from typing import Any, Dict, Iterable, List, Optional

import requests

API_HOST = "nascar-motorsport-api.p.rapidapi.com"
API_URL = f"https://{API_HOST}/standings-drivers"
DEFAULT_YEAR = 2025
OUTPUT_FILE = pathlib.Path("standings.html")


def _first_not_none(values: Iterable[Any]) -> Optional[Any]:
    for value in values:
        if value is not None:
            return value
    return None


def _extract_entries(payload: Any) -> List[Dict[str, Any]]:
    """Try a few common shapes to pull standings rows out of the response."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    # RapidAPI NASCAR feed often nests under "standings" -> "entries"
    if isinstance(payload, dict) and isinstance(payload.get("standings"), dict):
        nested = payload["standings"]
        entries = nested.get("entries")
        if isinstance(entries, list):
            return [row for row in entries if isinstance(row, dict)]

    if isinstance(payload, dict):
        candidates = [
            payload.get("response"),
            payload.get("results"),
            payload.get("data"),
            payload.get("standings"),
            payload.get("Standings"),
            payload.get("drivers"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, dict)]

    return []


def _name_from_entry(entry: Dict[str, Any]) -> str:
    athlete = entry.get("athlete")
    if isinstance(athlete, dict):
        athlete_name = _first_not_none(
            [
                athlete.get("displayName"),
                athlete.get("name"),
                athlete.get("shortName"),
            ]
        )
        if athlete_name:
            return str(athlete_name)

    driver = entry.get("driver") or entry.get("Driver")
    if isinstance(driver, dict):
        nested_name = _first_not_none(
            [
                driver.get("name"),
                driver.get("full_name"),
                driver.get("fullName"),
                driver.get("last_name"),
            ]
        )
        if nested_name:
            return str(nested_name)

    name = _first_not_none(
        [
            entry.get("driver_name"),
            entry.get("full_name"),
            entry.get("FullName"),
            entry.get("DriverName"),
            entry.get("name"),
        ]
    )
    return str(name) if name else "Unknown"


def _car_from_entry(entry: Dict[str, Any]) -> str:
    team = entry.get("team")
    if isinstance(team, dict):
        team_name = _first_not_none([team.get("displayName"), team.get("name"), team.get("abbreviation")])
        if team_name:
            return str(team_name)

    team = entry.get("team")
    if isinstance(team, dict) and team.get("name"):
        return str(team["name"])
    team_name = _first_not_none([entry.get("team_name"), entry.get("TeamName"), entry.get("team")])
    return str(team_name) if team_name else "-"


def _int_from_entry(entry: Dict[str, Any], keys: Iterable[str]) -> Optional[int]:
    # Some responses store numeric fields inside a stats list (ESPN style)
    stats_lookup = {}
    if isinstance(entry.get("stats"), list):
        for stat in entry["stats"]:
            if isinstance(stat, dict) and "name" in stat:
                stats_lookup[str(stat["name"])] = stat

    for key in keys:
        if key in entry:
            try:
                return int(entry[key])
            except (TypeError, ValueError):
                return None

        if key in stats_lookup:
            try:
                return int(stats_lookup[key].get("value"))
            except (TypeError, ValueError):
                return None
    return None


def _position(entry: Dict[str, Any]) -> Optional[int]:
    return _int_from_entry(entry, ["position", "pos", "rank", "driverStandingPos"])


def _points(entry: Dict[str, Any]) -> Optional[int]:
    return _int_from_entry(entry, ["points", "pts", "score", "championshipPts"])


def _wins(entry: Dict[str, Any]) -> Optional[int]:
    return _int_from_entry(entry, ["wins", "raceWins"])


def fetch_standings(year: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("NASCAR_API_KEY")
    if not api_key:
        raise SystemExit("Set RAPIDAPI_KEY (or NASCAR_API_KEY) with your RapidAPI key.")

    headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": API_HOST}
    response = requests.get(API_URL, headers=headers, params={"year": str(year)}, timeout=10)
    response.raise_for_status()

    payload = response.json()
    if os.getenv("STANDINGS_SAVE_RAW"):
        pathlib.Path("standings_raw.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return _extract_entries(payload)


def render_html(standings: List[Dict[str, Any]], year: int) -> str:
    rows = []
    for idx, entry in enumerate(standings, start=1):
        position = _position(entry) or idx
        name = html.escape(_name_from_entry(entry))
        team = html.escape(_car_from_entry(entry))
        points = _points(entry)
        wins = _wins(entry)
        rows.append(
            f"<tr><td>{position}</td><td>{name}</td><td>{team}</td>"
            f"<td>{points if points is not None else '-'}</td>"
            f"<td>{wins if wins is not None else '-'}</td></tr>"
        )

    if not rows:
        rows.append("<tr><td colspan='5'>No standings data returned.</td></tr>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NASCAR Driver Standings {year}</title>
  <style>
    body {{
      font-family: "Helvetica Neue", Arial, sans-serif;
      background: #0c1b33;
      color: #f5f7fa;
      margin: 0;
      padding: 24px;
    }}
    .card {{
      max-width: 960px;
      margin: 0 auto;
      background: #12264a;
      border: 1px solid #27467a;
      border-radius: 12px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
      overflow: hidden;
    }}
    header {{
      padding: 20px 24px;
      background: linear-gradient(135deg, #1f3e72, #0f2240);
    }}
    header h1 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0.02em;
    }}
    header p {{
      margin: 4px 0 0;
      color: #c3d4ef;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
    }}
    th {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #9ab7e5;
      border-bottom: 1px solid #213a63;
    }}
    tr:nth-child(odd) {{ background: #10203f; }}
    tr:nth-child(even) {{ background: #0d1a34; }}
    tr:hover {{ background: #1b325c; }}
    td:first-child {{
      width: 60px;
      font-weight: 700;
      color: #f0b429;
    }}
  </style>
</head>
<body>
  <div class="card">
    <header>
      <h1>NASCAR Driver Standings {year}</h1>
      <p>Live from RapidAPI &middot; generated at runtime</p>
    </header>
    <table aria-label="NASCAR driver standings">
      <thead>
        <tr><th>Pos</th><th>Driver</th><th>Team</th><th>Points</th><th>Wins</th></tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> None:
    year = int(os.getenv("STANDINGS_YEAR") or DEFAULT_YEAR)
    entries = fetch_standings(year)
    print(f"Fetched {len(entries)} standings entries for {year}.")
    html_content = render_html(entries, year)
    OUTPUT_FILE.write_text(html_content, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
