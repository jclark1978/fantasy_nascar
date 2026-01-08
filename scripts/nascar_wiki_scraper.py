#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag

WIKI_URL = "https://en.wikipedia.org/wiki/2026_NASCAR_Cup_Series"

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_SCHEDULE = BASE_DIR / "data/raw/nascar_2026_schedule.json"
OUT_TEAMS = BASE_DIR / "data/raw/nascar_2026_teams_and_drivers.json"

SEASON_YEAR = 2026
SERIES = "NASCAR Cup Series"

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}
KNOWN_MANUFACTURERS = {"Chevrolet", "Ford", "Toyota"}


# ----------------------------
# Helpers
# ----------------------------
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def abs_wiki(href: str) -> str:
    if href.startswith("/wiki/"):
        return "https://en.wikipedia.org" + href
    return href


def cell_text(cell: Tag) -> str:
    return normalize_ws(cell.get_text(" ", strip=True))


def first_link(cell: Tag) -> Tuple[Optional[str], Optional[str]]:
    a = cell.find("a", href=True)
    if not a:
        return None, None
    return normalize_ws(a.get_text(" ", strip=True)) or None, abs_wiki(a["href"]) or None


def parse_month_day_to_iso(season_year: int, md: Optional[str]) -> Optional[str]:
    if not md:
        return None
    md = normalize_ws(md)
    m = re.match(
        r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})$",
        md,
    )
    if not m:
        return None
    month_name, day_str = m.group(1), m.group(2)
    try:
        d = date(season_year, MONTHS[month_name], int(day_str))
        return d.isoformat()
    except Exception:
        return None


def parse_driver_cell(text: str) -> Tuple[str, bool]:
    """
    Wikipedia sometimes marks rookies like: "Connor Zilisch (R)"
    """
    t = normalize_ws(text)
    rookie = False
    m = re.match(r"^(.*)\s+\(R\)$", t)
    if m:
        rookie = True
        t = normalize_ws(m.group(1))
    return t, rookie


def looks_like_reference(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(re.match(r"^\[.+\]$", value.strip())) or value.strip().startswith("#cite")


def looks_like_car_no(value: Optional[str]) -> bool:
    return bool(value and value.strip().isdigit())


def is_unknown(value: Optional[str]) -> bool:
    return not value or value.strip().upper() == "TBA" or looks_like_reference(value)


def get_wikitable_by_headers(soup: BeautifulSoup, required_headers: List[str]) -> Optional[Tag]:
    """
    Find a wikitable whose first row contains all required header names (case-insensitive, substring match ok).
    """
    required = [h.lower() for h in required_headers]
    for table in soup.select("table.wikitable"):
        header_row = table.find("tr")
        if not header_row:
            continue
        headers = [normalize_ws(th.get_text(" ", strip=True)).lower() for th in header_row.find_all(["th", "td"])]
        # allow substring match ("Time (ET)" etc.)
        if all(any(req == h or req in h for h in headers) for req in required):
            return table
    return None


# ----------------------------
# Schedule
# ----------------------------
@dataclass
class ScheduleRace:
    season: int
    series: str
    phase: str                 # e.g. Regular Season, Round of 16, NASCAR Cup Series Playoffs, etc.
    race_no: Optional[int]     # None for non-championship events without a "No"
    name: Optional[str]
    name_wiki_url: Optional[str]
    track_type: Optional[str]  # "O", "R", "S" if available
    track: Optional[str]
    track_wiki_url: Optional[str]
    location: Optional[str]
    date_text: Optional[str]
    date_iso: Optional[str]
    time_et: Optional[str]
    tv: Optional[str]
    radio: Optional[str]


def extract_track_type_from_text(t: str) -> Optional[str]:
    # table uses " O " " R " " S " markers; easiest is to look for leading letter token
    t = normalize_ws(t)
    m = re.match(r"^(O|R|S)\b", t)
    return m.group(1) if m else None


def scrape_schedule(soup: BeautifulSoup) -> Dict[str, Any]:
    table = get_wikitable_by_headers(
        soup,
        required_headers=["No", "Race name", "Track", "Location", "Date"],
    )
    if not table:
        raise RuntimeError("Could not find schedule table with expected headers.")

    header_cells = table.find("tr").find_all(["th", "td"])
    headers = [normalize_ws(c.get_text(" ", strip=True)) for c in header_cells]

    def idx(col: str) -> Optional[int]:
        cl = col.lower()
        for i, h in enumerate(headers):
            hl = h.lower()
            if hl == cl or cl in hl:
                return i
        return None

    i_no = idx("No")
    i_race = idx("Race name")
    i_track = idx("Track")
    i_loc = idx("Location")
    i_date = idx("Date")
    i_time = idx("Time")   # matches "Time (ET)"
    i_tv = idx("TV")
    i_radio = idx("Radio")

    races: List[ScheduleRace] = []
    phase = "Regular Season"

    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue

        # Section/phase rows are often a single TH spanning columns
        if len(cells) == 1 and cells[0].name == "th":
            label = cell_text(cells[0])
            if label:
                phase = label
            continue

        def get_cell(i: Optional[int]) -> Optional[Tag]:
            if i is None or i < 0 or i >= len(cells):
                return None
            return cells[i]

        c_no = get_cell(i_no)
        c_race = get_cell(i_race)
        c_track = get_cell(i_track)
        c_loc = get_cell(i_loc)
        c_date = get_cell(i_date)
        c_time = get_cell(i_time)
        c_tv = get_cell(i_tv)
        c_radio = get_cell(i_radio)

        # race number
        race_no = None
        if c_no:
            no_txt = cell_text(c_no)
            if no_txt.isdigit():
                race_no = int(no_txt)

        # race name
        name, name_url = (None, None)
        if c_race:
            link_text, link_url = first_link(c_race)
            raw = cell_text(c_race)
            name = link_text or raw or None
            name_url = link_url

        # track + type
        track_type, track, track_url = (None, None, None)
        if c_track:
            raw_track = cell_text(c_track)
            track_type = extract_track_type_from_text(raw_track)
            link_text, link_url = first_link(c_track)
            # if link_text exists, it's usually the track; otherwise strip leading type letter if present
            track = link_text or raw_track
            if track_type and track:
                # clean "O Bowman Gray Stadium" -> "Bowman Gray Stadium"
                track = re.sub(r"^(O|R|S)\s+", "", track).strip()
            track_url = link_url

        location = cell_text(c_loc) if c_loc else None
        date_text = cell_text(c_date) if c_date else None
        time_et = cell_text(c_time) if c_time else None
        tv = cell_text(c_tv) if c_tv else None
        radio = cell_text(c_radio) if c_radio else None

        # Some rows on Wikipedia are incomplete; keep them, but don't crash
        if not any([race_no, name, track, location, date_text]):
            continue

        races.append(
            ScheduleRace(
                season=SEASON_YEAR,
                series=SERIES,
                phase=phase,
                race_no=race_no,
                name=name,
                name_wiki_url=name_url,
                track_type=track_type,
                track=track,
                track_wiki_url=track_url,
                location=location,
                date_text=date_text,
                date_iso=parse_month_day_to_iso(SEASON_YEAR, date_text),
                time_et=time_et,
                tv=tv,
                radio=radio,
            )
        )

    return {
        "source": WIKI_URL,
        "season": SEASON_YEAR,
        "series": SERIES,
        "races": [asdict(r) for r in races],
    }


# ----------------------------
# Teams & Drivers
# ----------------------------
@dataclass
class TeamDriverEntry:
    season: int
    series: str
    charter_status: str  # "chartered" | "non-chartered"
    manufacturer: Optional[str]
    manufacturer_wiki_url: Optional[str]
    team: Optional[str]
    team_wiki_url: Optional[str]
    car_no: Optional[str]
    driver: Optional[str]
    driver_wiki_url: Optional[str]
    rookie: Optional[bool]
    crew_chief: Optional[str]
    races: Optional[int]  # only for non-chartered
    references: Optional[str]


def scrape_teams_and_drivers(soup: BeautifulSoup) -> Dict[str, Any]:
    results: List[TeamDriverEntry] = []

    def parse_table(table: Tag, charter_status: str) -> None:
        header = table.find("tr")
        headers = [normalize_ws(c.get_text(" ", strip=True)) for c in header.find_all(["th", "td"])]

        def idx(col_name: str) -> Optional[int]:
            cn = col_name.lower()
            for i, h in enumerate(headers):
                hl = h.lower()
                if hl == cn or cn in hl:
                    return i
            return None

        i_manu = idx("Manufacturer")
        i_team = idx("Team")
        i_no = idx("No.")
        i_driver = idx("Driver")
        i_cc = idx("Crew chief")
        i_races = idx("Races")
        i_refs = idx("References")

        # handle rowspans by carrying forward last seen manufacturer/team
        current_manu = None
        current_manu_url = None
        current_team = None
        current_team_url = None

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue

            def get_cell(i: Optional[int]) -> Optional[Tag]:
                if i is None or i < 0 or i >= len(cells):
                    return None
                return cells[i]

            c_manu = get_cell(i_manu)
            c_team = get_cell(i_team)

        manu_txt = cell_text(c_manu) if c_manu else None
        team_txt = cell_text(c_team) if c_team else None
        car_no = cell_text(get_cell(i_no)) if get_cell(i_no) else None
        driver_txt = cell_text(get_cell(i_driver)) if get_cell(i_driver) else None
        original_car_no = car_no
        crew_chief = cell_text(get_cell(i_cc)) if get_cell(i_cc) else None

        if manu_txt:
            link_text, link_url = first_link(c_manu)
            candidate = link_text or manu_txt
            if candidate in KNOWN_MANUFACTURERS:
                current_manu = candidate
                current_manu_url = link_url

        if team_txt and not looks_like_car_no(team_txt):
            link_text, link_url = first_link(c_team)
            current_team = link_text or team_txt
            current_team_url = link_url

        # Handle rows where columns are shifted (common when Wikipedia tables change layout)
        team_override = None
        team_override_url = None
        if manu_txt and manu_txt not in KNOWN_MANUFACTURERS and looks_like_car_no(team_txt) and car_no and not looks_like_car_no(car_no):
            team_override = manu_txt
            team_override_url = first_link(c_manu)[1] if c_manu else None
            if looks_like_car_no(team_txt):
                car_no = team_txt
            if original_car_no and not is_unknown(original_car_no):
                driver_txt = original_car_no

        driver = None
        driver_url = None
        rookie = None
        if driver_txt and not is_unknown(driver_txt) and not looks_like_car_no(driver_txt):
            dname_raw = driver_txt
            dname, is_rookie = parse_driver_cell(dname_raw)
            driver = dname
            rookie = is_rookie
            if c_driver:
                link_text, link_url = first_link(c_driver)
                driver_url = link_url

        if is_unknown(crew_chief):
            crew_chief = None

            races = None
            c_races = get_cell(i_races)
            if c_races:
                rtxt = cell_text(c_races)
                if rtxt.isdigit():
                    races = int(rtxt)

            references = cell_text(get_cell(i_refs)) if get_cell(i_refs) else None

            # Skip rows that aren't actual car entries
            if not (car_no or driver or crew_chief):
                continue

            results.append(
                TeamDriverEntry(
                    season=SEASON_YEAR,
                    series=SERIES,
                    charter_status=charter_status,
                manufacturer=current_manu,
                manufacturer_wiki_url=current_manu_url,
                team=team_override or current_team,
                team_wiki_url=team_override_url or current_team_url,
                car_no=car_no if not is_unknown(car_no) else None,
                driver=driver,
                driver_wiki_url=driver_url,
                rookie=rookie,
                crew_chief=crew_chief,
                    races=races,
                    references=references,
                )
            )

    chartered = get_wikitable_by_headers(
        soup,
        required_headers=["Manufacturer", "Team", "No.", "Driver", "Crew chief"],
    )
    if not chartered:
        raise RuntimeError("Could not find chartered teams table.")
    parse_table(chartered, "chartered")

    non_chartered = get_wikitable_by_headers(
        soup,
        required_headers=["Manufacturer", "Team", "No.", "Driver", "Crew chief", "Races"],
    )
    if non_chartered:
        parse_table(non_chartered, "non-chartered")

    # Derived rollups for website filters
    manufacturers = sorted({e.manufacturer for e in results if e.manufacturer})
    teams = sorted({e.team for e in results if e.team})
    drivers = sorted({e.driver for e in results if e.driver})

    return {
        "source": WIKI_URL,
        "season": SEASON_YEAR,
        "series": SERIES,
        "entries": [asdict(e) for e in results],
        "derived": {
            "manufacturers": manufacturers,
            "teams": teams,
            "drivers": drivers,
        },
    }


# ----------------------------
# Main
# ----------------------------
def fetch_page() -> BeautifulSoup:
    resp = requests.get(
        WIKI_URL,
        headers={"User-Agent": "fantasy-nascar-wiki-scraper/1.0 (personal project)"},
        timeout=30,
    )
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    soup = fetch_page()

    schedule = scrape_schedule(soup)
    teams = scrape_teams_and_drivers(soup)

    write_json(OUT_SCHEDULE, schedule)
    write_json(OUT_TEAMS, teams)

    print(f"Wrote {OUT_SCHEDULE.resolve()}  ({len(schedule['races'])} rows)")
    print(f"Wrote {OUT_TEAMS.resolve()}  ({len(teams['entries'])} entries)")


if __name__ == "__main__":
    main()
