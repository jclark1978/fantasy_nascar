from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PickCreate(BaseModel):
    race_id: str
    driver_id: str


class PickOut(BaseModel):
    id: int
    user_id: int
    race_id: str
    driver_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LeagueCreate(BaseModel):
    name: str


class LeagueJoin(BaseModel):
    code: str


class LeagueSettingsOut(BaseModel):
    top_pick_count: int
    middle_pick_count: int
    bottom_pick_count: int
    top_rank_max: int
    middle_rank_max: int
    max_starts_per_driver: int
    lock_hours: int

    class Config:
        from_attributes = True


class LeagueSettingsUpdate(BaseModel):
    top_pick_count: Optional[int] = None
    middle_pick_count: Optional[int] = None
    bottom_pick_count: Optional[int] = None
    top_rank_max: Optional[int] = None
    middle_rank_max: Optional[int] = None
    max_starts_per_driver: Optional[int] = None
    lock_hours: Optional[int] = None


class LeagueOut(BaseModel):
    id: int
    name: str
    code: str
    commissioner_id: int
    created_at: datetime
    settings: Optional[LeagueSettingsOut]

    class Config:
        from_attributes = True


class LeagueMembershipOut(BaseModel):
    league: LeagueOut
    role: str


class LineupDriver(BaseModel):
    driver_id: str
    name: Optional[str]
    rank: Optional[int]
    used: int
    remaining: int


class LineupTier(BaseModel):
    starter_max: int
    bench_max: int
    drivers: List[LineupDriver]


class LineupEligibility(BaseModel):
    league_id: int
    race_id: str
    season_year: int
    lock_time: Optional[datetime]
    locked: bool
    settings: LeagueSettingsOut
    tiers: Dict[str, LineupTier]
    current_lineup: Optional[Dict]


class LineupEntryIn(BaseModel):
    driver_id: str
    tier: str
    role: str


class LineupCreate(BaseModel):
    league_id: int
    race_id: str
    season_year: int
    entries: List[LineupEntryIn]


class LineupEntryOut(BaseModel):
    driver_id: str
    tier: str
    role: str

    class Config:
        from_attributes = True


class LineupOut(BaseModel):
    id: int
    league_id: int
    user_id: int
    race_id: str
    season_year: int
    created_at: datetime
    updated_at: datetime
    entries: List[LineupEntryOut]

    class Config:
        from_attributes = True
