import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from .db import engine
from .auth import get_db, get_password_hash, verify_password, create_access_token, get_current_user
from .api_client import (
    get_upcoming_races,
    get_drivers_for_race,
    get_driver_standings,
    get_results_by_year,
    get_driver_stats,
    get_athlete_info,
    get_driver_photos,
)
from .cache import clear_cache

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fantasy NASCAR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _generate_league_code(db: Session) -> str:
    for _ in range(5):
        code = secrets.token_hex(3).upper()
        exists = db.query(models.League).filter(models.League.code == code).first()
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Unable to generate league code")


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_rank(entry: dict) -> int | None:
    for stat in entry.get("stats", []) or []:
        if stat.get("name") == "rank":
            try:
                return int(stat.get("value") or stat.get("displayValue"))
            except (TypeError, ValueError):
                return None
    try:
        return int(entry.get("rank"))
    except (TypeError, ValueError):
        return None


def _extract_driver(entry: dict) -> dict | None:
    athlete = entry.get("athlete") or entry.get("driver") or {}
    driver_id = athlete.get("id") or entry.get("driverId") or entry.get("athleteId")
    name = athlete.get("displayName") or athlete.get("fullName") or athlete.get("name")
    rank = _extract_rank(entry)
    if not driver_id or rank is None:
        return None
    return {"driver_id": str(driver_id), "name": name, "rank": rank}


def _get_usage_counts(
    db: Session, league_id: int, user_id: int, season_year: int, exclude_lineup_id: int | None = None
) -> dict:
    query = (
        db.query(models.LineupEntry.driver_id, func.count(models.LineupEntry.id))
        .join(models.Lineup)
        .filter(
            models.Lineup.league_id == league_id,
            models.Lineup.user_id == user_id,
            models.Lineup.season_year == season_year,
        )
    )
    if exclude_lineup_id:
        query = query.filter(models.Lineup.id != exclude_lineup_id)
    rows = query.group_by(models.LineupEntry.driver_id).all()
    return {row[0]: row[1] for row in rows}


@app.post("/auth/register", response_model=schemas.Token)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=user_in.email, hashed_password=get_password_hash(user_in.password), is_guest=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=schemas.Token)
def login(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/guest", response_model=schemas.Token)
def guest(db: Session = Depends(get_db)):
    # create a simple guest user to make testing easy
    guest_user = models.User(email=None, hashed_password=None, is_guest=True)
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    token = create_access_token({"sub": str(guest_user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/races/upcoming")
def upcoming_races(year: int = None):
    return get_upcoming_races(year)


@app.get("/drivers")
def drivers(raceId: str):
    return get_drivers_for_race(raceId)


@app.get("/standings/drivers")
def driver_standings(year: int, series: int = 1):
    return get_driver_standings(year, series)


@app.get("/results")
def results(year: int, series: int = 1):
    return get_results_by_year(year, series)


@app.get("/drivers/{driver_id}/stats")
def driver_stats(driver_id: str):
    return get_driver_stats(driver_id)


@app.get("/drivers/{driver_id}/info")
def driver_info(driver_id: str):
    return get_athlete_info(driver_id)


@app.get("/drivers/{driver_id}/photos")
def driver_photos(driver_id: str, page: int = 1):
    return get_driver_photos(driver_id, page)


@app.post("/leagues", response_model=schemas.LeagueOut)
def create_league(
    league_in: schemas.LeagueCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    code = _generate_league_code(db)
    league = models.League(name=league_in.name, code=code, commissioner_id=current_user.id)
    settings = models.LeagueSettings(league=league)
    db.add(league)
    db.add(settings)
    db.commit()
    db.refresh(league)
    member = models.LeagueMember(league_id=league.id, user_id=current_user.id, role="commissioner")
    db.add(member)
    db.commit()
    db.refresh(league)
    return league


@app.post("/leagues/join", response_model=schemas.LeagueOut)
def join_league(
    join_in: schemas.LeagueJoin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    league = db.query(models.League).filter(models.League.code == join_in.code.upper()).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    existing = (
        db.query(models.LeagueMember)
        .filter(models.LeagueMember.league_id == league.id, models.LeagueMember.user_id == current_user.id)
        .first()
    )
    if not existing:
        db.add(models.LeagueMember(league_id=league.id, user_id=current_user.id, role="member"))
        db.commit()
    db.refresh(league)
    return league


@app.get("/leagues/me", response_model=list[schemas.LeagueMembershipOut])
def my_leagues(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    memberships = (
        db.query(models.LeagueMember)
        .filter(models.LeagueMember.user_id == current_user.id)
        .all()
    )
    results = []
    for membership in memberships:
        league = db.query(models.League).filter(models.League.id == membership.league_id).first()
        if league:
            results.append({"league": league, "role": membership.role})
    return results


@app.patch("/leagues/{league_id}/settings", response_model=schemas.LeagueSettingsOut)
def update_league_settings(
    league_id: int,
    settings_in: schemas.LeagueSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    if league.commissioner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the commissioner can update settings")

    settings = league.settings
    if not settings:
        settings = models.LeagueSettings(league_id=league.id)
        db.add(settings)
        db.flush()

    for field, value in settings_in.dict(exclude_unset=True).items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


@app.get("/lineups/eligible", response_model=schemas.LineupEligibility)
def lineup_eligibility(
    league_id: int,
    race_id: str,
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or not league.settings:
        raise HTTPException(status_code=404, detail="League not found")

    season_year = year
    if season_year is None:
        try:
            season_year = int(race_id[:4])
        except (TypeError, ValueError):
            season_year = datetime.now(tz=timezone.utc).year

    schedule = get_upcoming_races(season_year)
    race_info = next((race for race in schedule if str(race.get("raceId")) == str(race_id)), None)
    race_date = _parse_datetime(race_info.get("date")) if race_info else None
    lock_time = race_date - timedelta(hours=league.settings.lock_hours) if race_date else None
    locked = False
    if lock_time:
        locked = datetime.now(tz=timezone.utc) >= lock_time

    standings_data = get_driver_standings(season_year, series=1)
    entries = standings_data.get("standings", {}).get("entries", []) if isinstance(standings_data, dict) else []
    drivers = [driver for driver in (_extract_driver(entry) for entry in entries) if driver]
    drivers.sort(key=lambda item: item["rank"])

    usage_counts = _get_usage_counts(db, league_id, current_user.id, season_year)

    def build_pool(min_rank: int | None, max_rank: int | None):
        pool = []
        for driver in drivers:
            rank = driver["rank"]
            if min_rank is not None and rank <= min_rank:
                continue
            if max_rank is not None and rank > max_rank:
                continue
            used = usage_counts.get(driver["driver_id"], 0)
            remaining = max(league.settings.max_starts_per_driver - used, 0)
            if remaining <= 0:
                continue
            pool.append(
                schemas.LineupDriver(
                    driver_id=driver["driver_id"],
                    name=driver["name"],
                    rank=rank,
                    used=used,
                    remaining=remaining,
                )
            )
        return pool

    top_pool = build_pool(None, league.settings.top_rank_max)
    middle_pool = build_pool(league.settings.top_rank_max, league.settings.middle_rank_max)
    bottom_pool = build_pool(league.settings.middle_rank_max, None)

    existing_lineup = (
        db.query(models.Lineup)
        .filter(
            models.Lineup.league_id == league_id,
            models.Lineup.user_id == current_user.id,
            models.Lineup.race_id == race_id,
        )
        .first()
    )
    current_lineup = None
    if existing_lineup:
        current_lineup = {
            "id": existing_lineup.id,
            "entries": [{"driver_id": entry.driver_id, "tier": entry.tier} for entry in existing_lineup.entries],
        }

    return schemas.LineupEligibility(
        league_id=league_id,
        race_id=race_id,
        season_year=season_year,
        lock_time=lock_time,
        locked=locked,
        settings=schemas.LeagueSettingsOut.model_validate(league.settings),
        tiers={
            "top": schemas.LineupTier(max_picks=league.settings.top_pick_count, drivers=top_pool),
            "middle": schemas.LineupTier(max_picks=league.settings.middle_pick_count, drivers=middle_pool),
            "bottom": schemas.LineupTier(max_picks=league.settings.bottom_pick_count, drivers=bottom_pool),
        },
        current_lineup=current_lineup,
    )


@app.post("/lineups", response_model=schemas.LineupOut)
def save_lineup(
    lineup_in: schemas.LineupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    league = db.query(models.League).filter(models.League.id == lineup_in.league_id).first()
    if not league or not league.settings:
        raise HTTPException(status_code=404, detail="League not found")

    member = (
        db.query(models.LeagueMember)
        .filter(
            models.LeagueMember.league_id == league.id,
            models.LeagueMember.user_id == current_user.id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a league member")

    schedule = get_upcoming_races(lineup_in.season_year)
    race_info = next((race for race in schedule if str(race.get("raceId")) == str(lineup_in.race_id)), None)
    race_date = _parse_datetime(race_info.get("date")) if race_info else None
    lock_time = race_date - timedelta(hours=league.settings.lock_hours) if race_date else None
    if lock_time and datetime.now(tz=timezone.utc) >= lock_time:
        raise HTTPException(status_code=400, detail="Lineups are locked for this race")

    entries_by_tier = {"top": [], "middle": [], "bottom": []}
    for entry in lineup_in.entries:
        if entry.tier not in entries_by_tier:
            raise HTTPException(status_code=400, detail=f"Unknown tier: {entry.tier}")
        entries_by_tier[entry.tier].append(entry.driver_id)

    if len(entries_by_tier["top"]) > league.settings.top_pick_count:
        raise HTTPException(status_code=400, detail="Too many top-tier selections")
    if len(entries_by_tier["middle"]) > league.settings.middle_pick_count:
        raise HTTPException(status_code=400, detail="Too many middle-tier selections")
    if len(entries_by_tier["bottom"]) > league.settings.bottom_pick_count:
        raise HTTPException(status_code=400, detail="Too many bottom-tier selections")

    standings_data = get_driver_standings(lineup_in.season_year, series=1)
    entries = standings_data.get("standings", {}).get("entries", []) if isinstance(standings_data, dict) else []
    drivers = [driver for driver in (_extract_driver(entry) for entry in entries) if driver]
    drivers.sort(key=lambda item: item["rank"])

    existing_lineup = (
        db.query(models.Lineup)
        .filter(
            models.Lineup.league_id == lineup_in.league_id,
            models.Lineup.user_id == current_user.id,
            models.Lineup.race_id == lineup_in.race_id,
        )
        .first()
    )

    usage_counts = _get_usage_counts(
        db,
        league.id,
        current_user.id,
        lineup_in.season_year,
        exclude_lineup_id=existing_lineup.id if existing_lineup else None,
    )

    def eligible_driver_ids(min_rank: int | None, max_rank: int | None) -> set[str]:
        eligible = set()
        for driver in drivers:
            rank = driver["rank"]
            if min_rank is not None and rank <= min_rank:
                continue
            if max_rank is not None and rank > max_rank:
                continue
            used = usage_counts.get(driver["driver_id"], 0)
            remaining = league.settings.max_starts_per_driver - used
            if remaining <= 0:
                continue
            eligible.add(driver["driver_id"])
        return eligible

    eligible_top = eligible_driver_ids(None, league.settings.top_rank_max)
    eligible_middle = eligible_driver_ids(league.settings.top_rank_max, league.settings.middle_rank_max)
    eligible_bottom = eligible_driver_ids(league.settings.middle_rank_max, None)
    tier_eligible = {"top": eligible_top, "middle": eligible_middle, "bottom": eligible_bottom}

    seen = set()
    request_counts = {}
    for entry in lineup_in.entries:
        if entry.driver_id in seen:
            raise HTTPException(status_code=400, detail="Duplicate driver selected")
        seen.add(entry.driver_id)
        if entry.driver_id not in tier_eligible[entry.tier]:
            raise HTTPException(status_code=400, detail="Driver not eligible for selected tier")
        request_counts[entry.driver_id] = request_counts.get(entry.driver_id, 0) + 1

    for driver_id, count in request_counts.items():
        if usage_counts.get(driver_id, 0) + count > league.settings.max_starts_per_driver:
            raise HTTPException(status_code=400, detail="Driver exceeds max starts limit")

    if existing_lineup:
        existing_lineup.entries = []
        lineup = existing_lineup
    else:
        lineup = models.Lineup(
            league_id=league.id,
            user_id=current_user.id,
            race_id=lineup_in.race_id,
            season_year=lineup_in.season_year,
        )
        db.add(lineup)
        db.flush()

    for entry in lineup_in.entries:
        lineup.entries.append(models.LineupEntry(driver_id=entry.driver_id, tier=entry.tier))

    db.commit()
    db.refresh(lineup)
    return lineup


@app.post("/picks", response_model=schemas.PickOut)
def create_pick(pick: schemas.PickCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new = models.Pick(user_id=current_user.id, race_id=pick.race_id, driver_id=pick.driver_id)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@app.get("/picks/me", response_model=list[schemas.PickOut])
def my_picks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    picks = db.query(models.Pick).filter(models.Pick.user_id == current_user.id).all()
    return picks


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/refresh")
def admin_refresh():
    """Clear the internal cache (useful for testing)."""
    clear_cache()
    return {"status": "cache_cleared"}
