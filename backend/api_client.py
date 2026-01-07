import os
import requests
import json
import time
from typing import List, Dict

from .cache import get_cache, set_cache

API_HOST = "nascar-motorsport-api.p.rapidapi.com"
BASE_URL = f"https://{API_HOST}"

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


def get_upcoming_races(year: int = None) -> List[Dict]:
    cache_key = f"upcoming:{year or 'all'}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

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
