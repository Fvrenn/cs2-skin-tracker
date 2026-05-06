"""
Script de seed pour les tests. À supprimer après validation.
Usage : python seed_test.py
"""
import asyncio

from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.skin import Skin
import app.models  # noqa: F401 — enregistre tous les modèles


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Skin))
        await db.execute(delete(User))
        await db.commit()

        user = User(email="test@test.com", password_hash="test")
        db.add(user)
        await db.flush()  # génère user.id avant de l'utiliser dans Skin

        skin = Skin(
            user_id=user.id,
            market_hash_name="AK-47 | Redline (Field-Tested)",
        )
        db.add(skin)
        await db.commit()

        print(f"User  : {user.id}  ({user.email})")
        print(f"Skin  : {skin.id}  ({skin.market_hash_name})")
        print("Seed OK")


if __name__ == "__main__":
    asyncio.run(seed())
