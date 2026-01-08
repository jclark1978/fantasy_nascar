from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_guest = Column(Boolean, default=False)

    picks = relationship("Pick", back_populates="user")
    memberships = relationship("LeagueMember", back_populates="user")
    lineups = relationship("Lineup", back_populates="user")


class League(Base):
    __tablename__ = "leagues"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    commissioner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    commissioner = relationship("User")
    members = relationship("LeagueMember", back_populates="league")
    settings = relationship("LeagueSettings", back_populates="league", uselist=False)
    lineups = relationship("Lineup", back_populates="league")


class LeagueMember(Base):
    __tablename__ = "league_members"
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    league = relationship("League", back_populates="members")
    user = relationship("User", back_populates="memberships")


class LeagueSettings(Base):
    __tablename__ = "league_settings"
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), unique=True, nullable=False)
    top_pick_count = Column(Integer, default=1)
    middle_pick_count = Column(Integer, default=2)
    bottom_pick_count = Column(Integer, default=1)
    top_rank_max = Column(Integer, default=9)
    middle_rank_max = Column(Integer, default=24)
    max_starts_per_driver = Column(Integer, default=5)
    lock_hours = Column(Integer, default=29)

    league = relationship("League", back_populates="settings")


class Pick(Base):
    __tablename__ = "picks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    race_id = Column(String, index=True)
    driver_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="picks")


class Lineup(Base):
    __tablename__ = "lineups"
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    race_id = Column(String, index=True, nullable=False)
    season_year = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    league = relationship("League", back_populates="lineups")
    user = relationship("User", back_populates="lineups")
    entries = relationship("LineupEntry", back_populates="lineup", cascade="all, delete-orphan")


class LineupEntry(Base):
    __tablename__ = "lineup_entries"
    id = Column(Integer, primary_key=True, index=True)
    lineup_id = Column(Integer, ForeignKey("lineups.id"), nullable=False)
    driver_id = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    role = Column(String, nullable=False, default="starter")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lineup = relationship("Lineup", back_populates="entries")
