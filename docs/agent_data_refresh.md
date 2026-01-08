# Data Refresh Agent Notes

This note captures the recommended long‑term refresh strategy for scraped NASCAR data.

## Data Sources
- Schedule + roster: Wikipedia scraper (`scripts/nascar_wiki_scraper.py`)
- Standings: NASCAR standings scraper (`scripts/driver_scraper.py`)
- Driver profiles: NASCAR driver profile scraper (`scripts/driver_profile_scraper.py`)
- Normalization: `scripts/normalize_scraped_data.py`

## Refresh Cadence
High‑frequency (after each race / weekly):
- Standings (rank/points)
- Results (when implemented)

Medium‑frequency (weekly or monthly):
- Driver profiles (photo/bio/crew chief/team)
- Roster changes (mid‑season swaps)

Low‑frequency (manual / pre‑season + ad‑hoc):
- Schedule

## Recommended Automation
Preferred: cron or scheduled job in the hosting environment.

Example cadence:
- Nightly (or weekly): standings + profiles + normalize
- Monthly: roster + normalize
- Manual: schedule + normalize

## Runtime Triggers (fallback)
If no scheduler is available:
- On admin action: call `/admin/refresh-data?season=YYYY&scrape_profiles=true`
- On login: check data age; only refresh if stale (e.g., >24h)

## TTL / Staleness Hints
Suggested max ages:
- Standings: 6–12 hours
- Profiles: 7 days
- Roster: 30 days
- Schedule: 90 days

## Notes
- Playwright is required for driver profiles and standings scraping.
- Avoid scraping on every user request; use caching and TTL checks.
