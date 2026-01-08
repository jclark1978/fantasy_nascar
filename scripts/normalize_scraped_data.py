#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional

KNOWN_MANUFACTURERS = {"Chevrolet", "Ford", "Toyota"}
NON_POINTS_KEYWORDS = {
    "clash",
    "duel",
    "all-star",
    "all star",
    "open",
    "shootout",
    "exhibition",
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unknown"


def camel_to_spaced(value: str) -> str:
    if " " in value:
        return value
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", value)


def looks_like_reference(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(re.match(r"^\[.+\]$", value.strip())) or value.strip().startswith("#cite")


def looks_like_car_no(value: Optional[str]) -> bool:
    return bool(value and value.strip().isdigit())


def looks_like_date_text(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(re.match(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}$", value.strip()))


def looks_like_time_text(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(re.search(r"\b(am|pm)\b", value.lower()))


def parse_month_day_to_iso(season_year: int, md: Optional[str]) -> Optional[str]:
    if not md:
        return None
    md = md.strip()
    m = re.match(
        r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})$",
        md,
    )
    if not m:
        return None
    month_name, day_str = m.group(1), m.group(2)
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    try:
        return date(season_year, month_map[month_name], int(day_str)).isoformat()
    except Exception:
        return None


def parse_points(value: Optional[str]) -> Dict[str, Optional[int]]:
    if not value:
        return {"points_total": None, "stage_points": None}
    text = str(value)
    total_match = re.search(r"(\d+)", text)
    stage_match = re.search(r"\((\d+)\)", text)
    return {
        "points_total": int(total_match.group(1)) if total_match else None,
        "stage_points": int(stage_match.group(1)) if stage_match else None,
    }


def parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or looks_like_reference(text) or text.upper() == "TBA":
        return None
    m = re.match(r"^-?\d+$", text)
    if not m:
        return None
    return int(text)


def normalize_schedule(raw: Dict[str, Any], season: int) -> Dict[str, Any]:
    races = []
    for idx, race in enumerate(raw.get("races", []), start=1):
        name = (race.get("name") or "").strip() or f"Race {idx}"
        phase = race.get("phase") or "Regular Season"
        race_no = race.get("race_no")
        track = race.get("track")
        location = race.get("location")
        date_text = race.get("date_text")
        time_et = race.get("time_et")
        tv = race.get("tv")
        radio = race.get("radio")

        if not race.get("date_iso") and looks_like_date_text(location) and looks_like_time_text(date_text):
            date_text, location = location, None
            if time_et and tv is None and not looks_like_time_text(time_et):
                tv, time_et = time_et, date_text

        start_date = race.get("date_iso") or parse_month_day_to_iso(season, date_text)
        race_id = f"{season}-{race_no or idx:02d}-{slugify(name)}"
        is_points_race = not any(keyword in name.lower() for keyword in NON_POINTS_KEYWORDS)

        races.append(
            {
                "race_id": race_id,
                "name": name,
                "phase": phase,
                "race_no": race_no,
                "track": track,
                "track_type": race.get("track_type"),
                "location": location,
                "start_date": start_date,
                "start_time_et": time_et,
                "tv": tv,
                "radio": radio,
                "is_points_race": is_points_race,
                "source": {
                    "name_wiki_url": race.get("name_wiki_url"),
                    "track_wiki_url": race.get("track_wiki_url"),
                },
            }
        )

    return {
        "source": raw.get("source"),
        "season": season,
        "series": raw.get("series"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "races": races,
    }


def choose_driver_name(entry: Dict[str, Any]) -> Optional[str]:
    candidates = [entry.get("driver"), entry.get("team"), entry.get("car_no")]
    for cand in candidates:
        if not cand:
            continue
        cand = str(cand).strip()
        if cand.upper() == "TBA" or looks_like_reference(cand):
            continue
        if looks_like_car_no(cand):
            continue
        if any(token in cand for token in ["Racing", "Motorsports", "Club", "Team", "Garage"]):
            continue
        return camel_to_spaced(cand)
    return None


def normalize_roster(raw: Dict[str, Any], season: int) -> Dict[str, Any]:
    drivers = []
    issues = []
    for entry in raw.get("entries", []):
        manufacturer = entry.get("manufacturer")
        team = entry.get("team")
        car_no = entry.get("car_no")
        driver_name = choose_driver_name(entry)
        crew_chief = entry.get("crew_chief")

        if manufacturer and manufacturer not in KNOWN_MANUFACTURERS and not looks_like_car_no(manufacturer):
            if team and looks_like_car_no(team) and (car_no and not looks_like_car_no(car_no)):
                team, car_no, driver_name = manufacturer, team, camel_to_spaced(str(car_no))
                manufacturer = None

        if not driver_name and team and isinstance(team, str):
            if team.upper() != "TBA" and not looks_like_reference(team) and not looks_like_car_no(team):
                if not any(token in team for token in ["Racing", "Motorsports", "Club", "Team", "Garage"]):
                    driver_name = camel_to_spaced(team)

        if not looks_like_car_no(car_no) and crew_chief and crew_chief.upper() != "TBA":
            if not any(token in str(crew_chief) for token in ["Racing", "Motorsports", "Club", "Team", "Garage"]):
                if " " in str(car_no or "") and not looks_like_reference(str(car_no)):
                    crew_chief = car_no
                    car_no = manufacturer if looks_like_car_no(str(manufacturer)) else car_no

        if driver_name is None:
            issues.append({"reason": "missing_driver_name", "entry": entry})
            continue

        if not car_no and looks_like_car_no(entry.get("manufacturer")):
            car_no = entry.get("manufacturer")

        drivers.append(
            {
                "driver_name": driver_name,
                "driver_slug": slugify(driver_name),
                "team": team if isinstance(team, str) else None,
                "car_no": str(car_no) if car_no else None,
                "manufacturer": manufacturer if manufacturer in KNOWN_MANUFACTURERS else None,
                "charter_status": entry.get("charter_status"),
                "rookie": entry.get("rookie"),
                "crew_chief": crew_chief,
                "source": {"driver_wiki_url": entry.get("driver_wiki_url")},
            }
        )

    return {
        "source": raw.get("source"),
        "season": season,
        "series": raw.get("series"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "drivers": drivers,
        "issues": issues,
    }


def normalize_standings(raw: Dict[str, Any], season: int) -> Dict[str, Any]:
    target_table = None
    for table in raw.get("tables", []):
        cols = [c.upper() for c in table.get("columns", [])]
        if "POS" in cols and "DRIVER" in cols:
            target_table = table
            break

    standings = []
    issues = []
    if target_table:
        for row in target_table.get("rows", []):
            driver_raw = row.get("DRIVER")
            if not driver_raw or looks_like_reference(driver_raw):
                continue
            driver_name = camel_to_spaced(str(driver_raw).strip())
            points_info = parse_points(row.get("POINTS(STAGE)"))
            standings.append(
                {
                    "rank": parse_int(row.get("POS")),
                    "driver_name": driver_name,
                    "driver_slug": slugify(driver_name),
                    "points_total": points_info["points_total"],
                    "stage_points": points_info["stage_points"],
                    "behind": parse_int(row.get("BEHIND")),
                    "starts": parse_int(row.get("STARTS")),
                    "wins": parse_int(row.get("WINS")),
                    "top5": parse_int(row.get("TOP 5s")),
                    "top10": parse_int(row.get("TOP 10s")),
                    "dnfs": parse_int(row.get("DNFs")),
                    "laps_led": parse_int(row.get("LAPS LED")),
                    "playoff_points": parse_int(row.get("PLAYOFF POINTS")),
                }
            )
    else:
        issues.append({"reason": "no_standings_table"})

    return {
        "source": raw.get("source"),
        "season": season,
        "series": "NASCAR Cup Series",
        "scraped_at_utc": raw.get("scraped_at_utc"),
        "as_of": raw.get("as_of"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "standings": standings,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize scraped NASCAR data into canonical JSON files.")
    parser.add_argument("--schedule", required=True, help="Path to nascar_YYYY_schedule.json")
    parser.add_argument("--roster", required=True, help="Path to nascar_YYYY_teams_and_drivers.json")
    parser.add_argument("--standings", required=True, help="Path to nascar_cup_standings.json")
    parser.add_argument("--season", type=int, required=True, help="Season year for normalized outputs")
    parser.add_argument("--out-dir", required=True, help="Output directory for normalized JSON files")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    schedule_raw = json.loads(Path(args.schedule).read_text(encoding="utf-8"))
    roster_raw = json.loads(Path(args.roster).read_text(encoding="utf-8"))
    standings_raw = json.loads(Path(args.standings).read_text(encoding="utf-8"))

    schedule_norm = normalize_schedule(schedule_raw, args.season)
    roster_norm = normalize_roster(roster_raw, args.season)
    standings_norm = normalize_standings(standings_raw, args.season)

    (out_dir / f"schedule_{args.season}.json").write_text(
        json.dumps(schedule_norm, indent=2), encoding="utf-8"
    )
    (out_dir / f"roster_{args.season}.json").write_text(
        json.dumps(roster_norm, indent=2), encoding="utf-8"
    )
    (out_dir / f"standings_{args.season}.json").write_text(
        json.dumps(standings_norm, indent=2), encoding="utf-8"
    )

    print(f"Wrote {out_dir / f'schedule_{args.season}.json'}")
    print(f"Wrote {out_dir / f'roster_{args.season}.json'}")
    print(f"Wrote {out_dir / f'standings_{args.season}.json'}")


if __name__ == "__main__":
    main()
