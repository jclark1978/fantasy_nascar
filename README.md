# NASCAR fantasy league helper

`fetch_week_racers.py` exposes `fetch_week_racers(series_id=1)` which tries the live on-track feed first (`/api/LiveFeed?v=1`) and, if that is inactive or too small, falls back to the season driver roster (`/api/Driver?series_id=&race_season=`). LiveFeed only works during active sessions; otherwise expect the season roster to be used.

Run it directly to print the JSON output:

```bash
python3 fetch_week_racers.py
```

Optional: set `FEED_NASCAR_USER` and `FEED_NASCAR_PASS` if your feed endpoint requires Basic auth.
# fantasy_nascar
