# Data Schema (Canonical)

This project uses normalized JSON outputs that map scraped data into a stable shape.

Raw scraper outputs live in `data/raw/`, normalized outputs live in `data/normalized/`.

## Pipeline

Scrape schedule + roster (Wikipedia):
```bash
python3 scripts/nascar_wiki_scraper.py
```

Scrape standings (nascar.com):
```bash
python3 scripts/driver_scraper.py
```

Normalize raw outputs:
```bash
python3 scripts/normalize_scraped_data.py \
  --schedule data/raw/nascar_2026_schedule.json \
  --roster data/raw/nascar_2026_teams_and_drivers.json \
  --standings data/raw/nascar_cup_standings.json \
  --season 2026 \
  --out-dir data/normalized
```

Scrape driver profile pages (Playwright):
```bash
python3 scripts/driver_profile_scraper.py --season 2026
```

## Schedule (`schedule_YYYY.json`)

```json
{
  "source": "https://en.wikipedia.org/wiki/2026_NASCAR_Cup_Series",
  "season": 2026,
  "series": "NASCAR Cup Series",
  "generated_at_utc": "2026-01-07T20:00:00+00:00",
  "races": [
    {
      "race_id": "2026-01-cook-out-clash",
      "name": "Cook Out Clash",
      "phase": "Regular Season",
      "race_no": null,
      "track": "Bowman Gray Stadium",
      "track_type": "O",
      "location": "Winston-Salem, North Carolina",
      "start_date": "2026-02-01",
      "start_time_et": "8 pm",
      "tv": "FOX",
      "radio": "MRN",
      "is_points_race": false,
      "source": {
        "name_wiki_url": "https://en.wikipedia.org/wiki/Cook_Out_Clash_at_Bowman_Gray_Stadium",
        "track_wiki_url": "https://en.wikipedia.org/wiki/Bowman_Gray_Stadium"
      }
    }
  ]
}
```

Notes:
- `race_id` is generated as `{season}-{race_no or index}-{slug(name)}`.
- `is_points_race` is `false` for Clash/Duel/All‑Star/Open/Exhibition.
- `start_time_et` remains a string when only “8 pm” style values exist.

## Roster (`roster_YYYY.json`)

```json
{
  "source": "https://en.wikipedia.org/wiki/2026_NASCAR_Cup_Series",
  "season": 2026,
  "series": "NASCAR Cup Series",
  "generated_at_utc": "2026-01-07T20:00:00+00:00",
  "drivers": [
    {
      "driver_name": "Kyle Larson",
      "driver_slug": "kyle-larson",
      "team": "Hendrick Motorsports",
      "car_no": "5",
      "manufacturer": "Chevrolet",
      "charter_status": "chartered",
      "rookie": false,
      "crew_chief": "TBA",
      "source": {
        "driver_wiki_url": "https://en.wikipedia.org/wiki/Kyle_Larson"
      }
    }
  ],
  "issues": [
    {
      "reason": "missing_driver_name",
      "entry": { "..." : "raw scraper entry" }
    }
  ]
}
```

Notes:
- `driver_name` is derived by best‑effort parsing (CamelCase is split).
- `issues` lists entries that could not be normalized cleanly.

## Standings (`standings_YYYY.json`)

```json
{
  "source": "https://www.nascar.com/standings/nascar-cup-series/",
  "season": 2026,
  "series": "NASCAR Cup Series",
  "scraped_at_utc": "2026-01-07T18:05:09.408348+00:00",
  "as_of": "After Phoenix - November 2nd, 2025 - Race 36 of 36",
  "generated_at_utc": "2026-01-07T20:00:00+00:00",
  "standings": [
    {
      "rank": 1,
      "driver_name": "Kyle Larson",
      "driver_slug": "kyle-larson",
      "points_total": 5034,
      "stage_points": 297,
      "behind": 0,
      "starts": 36,
      "wins": 3,
      "top5": 15,
      "top10": 22,
      "dnfs": 2,
      "laps_led": 1106,
      "playoff_points": 32
    }
  ],
  "issues": []
}
```

Notes:
- `points_total` and `stage_points` are parsed from `"POINTS(STAGE)"`.
- `driver_name` is CamelCase‑split when needed.
