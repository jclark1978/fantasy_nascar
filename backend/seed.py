"""Seed script to create test users and a league for local development."""
from backend.db import SessionLocal
from backend.models import User, League, LeagueMember, LeagueSettings
from backend.auth import get_password_hash


def seed():
    db = SessionLocal()
    try:
        commissioner_email = "commissioner@example.com"
        member_email = "member@example.com"

        commissioner = db.query(User).filter(User.email == commissioner_email).first()
        if not commissioner:
            commissioner = User(
                email=commissioner_email,
                hashed_password=get_password_hash("password123"),
                is_guest=False,
            )
            db.add(commissioner)
            db.commit()
            db.refresh(commissioner)
            print(f"Created commissioner: {commissioner_email} / password123")
        else:
            print(f"Commissioner exists: {commissioner_email}")

        member = db.query(User).filter(User.email == member_email).first()
        if not member:
            member = User(
                email=member_email,
                hashed_password=get_password_hash("password123"),
                is_guest=False,
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            print(f"Created member: {member_email} / password123")
        else:
            print(f"Member exists: {member_email}")

        league = db.query(League).filter(League.code == "TEST01").first()
        if not league:
            league = League(name="Test League", code="TEST01", commissioner_id=commissioner.id)
            db.add(league)
            db.flush()
            settings = LeagueSettings(league_id=league.id)
            db.add(settings)
            db.commit()
            print("Created league: Test League (code TEST01)")
        else:
            print("League exists: Test League (code TEST01)")

        commissioner_member = (
            db.query(LeagueMember)
            .filter(LeagueMember.league_id == league.id, LeagueMember.user_id == commissioner.id)
            .first()
        )
        if not commissioner_member:
            db.add(LeagueMember(league_id=league.id, user_id=commissioner.id, role="commissioner"))
            db.commit()

        member_member = (
            db.query(LeagueMember)
            .filter(LeagueMember.league_id == league.id, LeagueMember.user_id == member.id)
            .first()
        )
        if not member_member:
            db.add(LeagueMember(league_id=league.id, user_id=member.id, role="member"))
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
