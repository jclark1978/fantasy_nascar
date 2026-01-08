import os
import requests
import json
import time
import re
import html as html_lib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

from .cache import get_cache, set_cache

API_HOST = "nascar-motorsport-api.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}"
BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_NORMALIZED_DIR = BASE_DIR / "data" / "normalized"
LOCAL_PROFILE_DIR = BASE_DIR / "data" / "raw" / "driver_profiles"

# retry/backoff configuration (ms -> seconds)
BACKOFF = [0.5, 1.5, 4.0]


def _rapidapi_headers():
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        return None
    return {"x-rapidapi-key": key, "x-rapidapi-host": API_HOST}


def _attempt_get(path: str, params: Dict = None):
    headers = _rapidapi_headers()
    if not headers:
        raise RuntimeError("No RAPIDAPI_KEY configured")
    url = f"{BASE_URL}{path}"
    last_exc = None
    for delay in BACKOFF:
        try:
            resp = requests.get(url, headers=headers, params=params or {}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
    raise last_exc


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unknown"


def _load_local_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _local_schedule(year: int) -> Optional[List[Dict]]:
    path = LOCAL_NORMALIZED_DIR / f"schedule_{year}.json"
    data = _load_local_json(path)
    if not data:
        return None
    races = []
    for race in data.get("races", []):
        date_value = race.get("start_date") or race.get("date")
        races.append(
            {
                "raceId": race.get("race_id"),
                "name": race.get("name"),
                "date": date_value,
                "track": race.get("track"),
                "series": data.get("series"),
            }
        )
    return races


def _local_standings(year: int) -> Optional[Dict]:
    path = LOCAL_NORMALIZED_DIR / f"standings_{year}.json"
    data = _load_local_json(path)
    if not data:
        return None
    entries = []
    for row in data.get("standings", []):
        driver_name = row.get("driver_name")
        driver_slug = row.get("driver_slug") or driver_name
        stats = [
            {"name": "rank", "value": row.get("rank"), "displayValue": str(row.get("rank")) if row.get("rank") is not None else None},
            {"name": "championshipPts", "value": row.get("points_total"), "displayValue": str(row.get("points_total")) if row.get("points_total") is not None else None},
            {"name": "stagePoints", "value": row.get("stage_points"), "displayValue": str(row.get("stage_points")) if row.get("stage_points") is not None else None},
            {"name": "wins", "value": row.get("wins"), "displayValue": str(row.get("wins")) if row.get("wins") is not None else None},
            {"name": "top5", "value": row.get("top5"), "displayValue": str(row.get("top5")) if row.get("top5") is not None else None},
            {"name": "top10", "value": row.get("top10"), "displayValue": str(row.get("top10")) if row.get("top10") is not None else None},
        ]
        entries.append(
            {
                "athlete": {
                    "id": driver_slug,
                    "displayName": driver_name,
                    "fullName": driver_name,
                },
                "stats": stats,
            }
        )
    return {"standings": {"season": year, "entries": entries}}


def _local_roster(year: int) -> Optional[Dict]:
    path = LOCAL_NORMALIZED_DIR / f"roster_{year}.json"
    return _load_local_json(path)


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def _load_local_profile_html(slug: str) -> Optional[str]:
    candidates = [
        LOCAL_PROFILE_DIR / f"{slug}.html",
    ]
    for path in candidates:
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                continue
    return None


def _extract_json_ld(html: str) -> list[Dict[str, Any]]:
    blocks = []
    for match in re.finditer(r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", html, re.S | re.I):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                blocks.extend([d for d in data if isinstance(d, dict)])
            elif isinstance(data, dict):
                blocks.append(data)
        except Exception:
            continue
    return blocks


def _extract_meta(html: str, name: str) -> Optional[str]:
    pattern = rf"<meta[^>]+property=\"{re.escape(name)}\"[^>]+content=\"(.*?)\""
    match = re.search(pattern, html, re.I | re.S)
    if match:
        return match.group(1).strip()
    pattern = rf"<meta[^>]+name=\"{re.escape(name)}\"[^>]+content=\"(.*?)\""
    match = re.search(pattern, html, re.I | re.S)
    if match:
        return match.group(1).strip()
    return None


def _find_first_value(obj: Any, keys: set[str]) -> Optional[Any]:
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for k, v in current.items():
                if k in keys and v:
                    return v
                stack.append(v)
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _extract_next_data(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"<script[^>]+id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>", html, re.S | re.I)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _lookup_standings(slug: str, year: int) -> Dict[str, Optional[int]]:
    data = _local_standings(year)
    if not data:
        return {"rank": None, "points": None}
    for entry in data.get("standings", {}).get("entries", []):
        athlete = entry.get("athlete", {})
        name = athlete.get("displayName") or athlete.get("fullName") or athlete.get("name")
        if not name:
            continue
        if _slugify(str(name)) != slug:
            continue
        rank = None
        points = None
        for stat in entry.get("stats", []):
            if stat.get("name") == "rank":
                rank = stat.get("value")
            if stat.get("name") == "championshipPts":
                points = stat.get("value")
        return {"rank": rank, "points": points}
    return {"rank": None, "points": None}


def _extract_profile_from_html(html: str) -> Dict[str, Optional[str]]:
    profile = {
        "name": None,
        "photo_url": None,
        "car_no": None,
        "dob": None,
        "hometown": None,
        "crew_chief": None,
        "team": None,
        "bio": None,
    }

    name_match = re.search(
        r"<div class=\"ndms2023-driver-name\">\s*<h1>\s*<span>(.*?)</span>\s*<br>\s*(.*?)</h1>",
        html,
        re.S | re.I,
    )
    if name_match:
        first = html_lib.unescape(name_match.group(1)).strip()
        last = html_lib.unescape(name_match.group(2)).strip()
        profile["name"] = f"{first} {last}".strip()

    photo_match = re.search(
        r"<div class=\"ndms2023-driver-hero-left-col\">.*?<img[^>]+src=\"([^\"]+)\"",
        html,
        re.S | re.I,
    )
    if photo_match:
        profile["photo_url"] = html_lib.unescape(photo_match.group(1)).strip()

    badge_match = re.search(
        r"class=\"ndms2023-driver-badge\".*?<img[^>]+src=\"([^\"]+)\"",
        html,
        re.S | re.I,
    )
    if badge_match:
        src = html_lib.unescape(badge_match.group(1))
        num_match = re.search(r"/(\\d{1,3})(?:@|\\-|\\.png)", src)
        if num_match:
            profile["car_no"] = num_match.group(1)

    bio_match = re.search(
        r"<div class=\"ndms2023-bio-container\">.*?<span>(.*?)</span>",
        html,
        re.S | re.I,
    )
    if bio_match:
        bio = html_lib.unescape(bio_match.group(1))
        bio = re.sub(r"\s+", " ", bio).strip()
        profile["bio"] = bio

    for match in re.finditer(
        r"<div class=\"ndms2023-driver-hero-right-row-4-col\">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>",
        html,
        re.S | re.I,
    ):
        label = html_lib.unescape(match.group(1)).strip().upper()
        value = html_lib.unescape(match.group(2))
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            continue
        if "DATE OF BIRTH" in label:
            profile["dob"] = value
        elif "HOMETOWN" in label:
            profile["hometown"] = value
        elif "CREW CHIEF" in label:
            profile["crew_chief"] = value
        elif "TEAM" in label:
            profile["team"] = value

    return profile


def get_upcoming_races(year: int = None) -> List[Dict]:
    cache_key = f"upcoming:{year or 'all'}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    if year:
        local_races = _local_schedule(year)
        if local_races is not None:
            set_cache(cache_key, local_races, ttl=300)
            return local_races

    # Try live API
    try:
        data = _attempt_get("/schedule", params={"year": str(year)} if year else None)
        # normalize
        if isinstance(data, dict) and data.get("results"):
            races = data["results"]
        elif isinstance(data, dict) and data.get("schedule"):
            races = data["schedule"]
        elif isinstance(data, list):
            races = data
        else:
            races = []
        set_cache(cache_key, races, ttl=300)
        return races
    except Exception:
        # fallback to sample
        sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_races.json")
        try:
            with open(sample_path, "r", encoding="utf-8") as fh:
                races = json.load(fh)
                set_cache(cache_key, races, ttl=300)
                return races
        except Exception:
            return []


def get_drivers_for_race(race_id: str) -> List[Dict]:
    cache_key = f"drivers:{race_id}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        data = _attempt_get("/race-results", params={"raceId": race_id})
        if isinstance(data, dict) and data.get("results"):
            drivers = data["results"]
        elif isinstance(data, list):
            drivers = data
        else:
            drivers = []
        set_cache(cache_key, drivers, ttl=300)
        return drivers
    except Exception:
        return []


def get_driver_standings(year: int, series: int = 1) -> Dict:
    cache_key = f"standings:{year}:{series}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    local = _local_standings(year)
    if local is not None:
        set_cache(cache_key, local, ttl=300)
        return local

    try:
        params = {"year": str(year)}
        if series is not None:
            params["series"] = str(series)
        data = _attempt_get("/standings-drivers", params=params)
        if isinstance(data, dict):
            set_cache(cache_key, data, ttl=300)
            return data
    except Exception:
        pass

    fallback_path = os.path.join(os.path.dirname(__file__), "..", "ARCHIVE", "standings_raw.json")
    try:
        with open(fallback_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            set_cache(cache_key, data, ttl=300)
            return data
    except Exception:
        return {}


def get_results_by_year(year: int, series: int = 1) -> List[Dict]:
    cache_key = f"results:{year}:{series}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        data = _attempt_get("/results", params={"year": str(year), "series": str(series)})
        if isinstance(data, list):
            set_cache(cache_key, data, ttl=300)
            return data
        if isinstance(data, dict) and data.get("results"):
            results = data["results"]
            set_cache(cache_key, results, ttl=300)
            return results
    except Exception:
        pass

    return []


def get_driver_stats(driver_id: str) -> List[Dict]:
    cache_key = f"driver-stats:{driver_id}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        data = _attempt_get("/stats", params={"driverId": str(driver_id)})
        if isinstance(data, list):
            set_cache(cache_key, data, ttl=300)
            return data
    except Exception:
        pass
    return []


def get_athlete_info(athlete_id: str) -> Dict:
    cache_key = f"athlete:{athlete_id}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        data = _attempt_get("/athlete-info", params={"athleteId": str(athlete_id)})
        if isinstance(data, dict):
            set_cache(cache_key, data, ttl=300)
            return data
    except Exception:
        pass
    return {}


def get_driver_photos(driver_id: str, page: int = 1) -> List[Dict]:
    cache_key = f"driver-photos:{driver_id}:{page}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        data = _attempt_get("/photos", params={"driverId": str(driver_id), "page": str(page)})
        if isinstance(data, list):
            set_cache(cache_key, data, ttl=300)
            return data
    except Exception:
        pass
    return []


def get_driver_profile(slug: str, year: int | None = None) -> Dict:
    if year is None:
        year = datetime.now(tz=timezone.utc).year
    cache_key = f"driver-profile:{slug}:{year}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    url = f"https://www.nascar.com/drivers/{slug}"
    headers = {
        "User-Agent": "fantasy-nascar-profile/1.0 (+https://nascar.com)",
    }
    profile = {
        "slug": slug,
        "name": None,
        "photo_url": None,
        "car_no": None,
        "dob": None,
        "hometown": None,
        "crew_chief": None,
        "team": None,
        "bio": None,
        "rank": None,
        "points": None,
        "source_url": url,
    }

    html = None
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        html = _load_local_profile_html(slug)

    if html:
        json_ld_blocks = _extract_json_ld(html)
        for block in json_ld_blocks:
            if block.get("@type") == "Person":
                profile["name"] = block.get("name") or profile["name"]
                profile["photo_url"] = block.get("image") or profile["photo_url"]
                profile["dob"] = block.get("birthDate") or profile["dob"]
                address = block.get("address") or {}
                if isinstance(address, dict):
                    locality = address.get("addressLocality")
                    region = address.get("addressRegion")
                    country = address.get("addressCountry")
                    hometown = ", ".join([v for v in [locality, region, country] if v])
                    if hometown:
                        profile["hometown"] = hometown

        next_data = _extract_next_data(html)
        if next_data:
            name = _find_first_value(next_data, {"fullName", "name", "displayName"})
            if isinstance(name, str):
                profile["name"] = profile["name"] or name
            photo = _find_first_value(next_data, {"headshot", "image", "photo", "headshotUrl"})
            if isinstance(photo, dict):
                profile["photo_url"] = profile["photo_url"] or photo.get("href") or photo.get("url")
            elif isinstance(photo, str):
                profile["photo_url"] = profile["photo_url"] or photo
            dob = _find_first_value(next_data, {"dateOfBirth", "birthDate"})
            if isinstance(dob, str):
                profile["dob"] = profile["dob"] or dob
            hometown = _find_first_value(next_data, {"hometown", "homeTown", "birthPlace"})
            if isinstance(hometown, str):
                profile["hometown"] = profile["hometown"] or hometown
            elif isinstance(hometown, dict):
                parts = [hometown.get("city"), hometown.get("state"), hometown.get("country")]
                hometown_str = ", ".join([p for p in parts if p])
                if hometown_str:
                    profile["hometown"] = profile["hometown"] or hometown_str
            team = _find_first_value(next_data, {"team", "teamName", "organization"})
            if isinstance(team, str):
                profile["team"] = profile["team"] or team
            crew_chief = _find_first_value(next_data, {"crewChief", "crewChiefName"})
            if isinstance(crew_chief, str):
                profile["crew_chief"] = profile["crew_chief"] or crew_chief
            bio = _find_first_value(next_data, {"bio", "biography", "shortBio"})
            if isinstance(bio, str):
                profile["bio"] = profile["bio"] or bio

        if not profile["photo_url"]:
            profile["photo_url"] = _extract_meta(html, "og:image")
        if not profile["bio"]:
            profile["bio"] = _extract_meta(html, "og:description")

        html_profile = _extract_profile_from_html(html)
        for key, value in html_profile.items():
            if value and not profile.get(key):
                profile[key] = value

    standings = _lookup_standings(slug, year)
    profile["rank"] = standings.get("rank")
    profile["points"] = standings.get("points")

    if not profile["name"]:
        profile["name"] = _title_from_slug(slug)

    roster = _local_roster(year)
    if roster:
        for driver in roster.get("drivers", []):
            if driver.get("driver_slug") != slug:
                continue
            profile["name"] = profile["name"] or driver.get("driver_name")
            profile["team"] = profile["team"] or driver.get("team")
            profile["crew_chief"] = profile["crew_chief"] or driver.get("crew_chief")
            profile["car_no"] = profile["car_no"] or driver.get("car_no")
            break

    set_cache(cache_key, profile, ttl=86400)
    return profile
