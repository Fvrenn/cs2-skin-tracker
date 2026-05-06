from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserSettings, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _user_to_schema(user: User) -> UserSettings:
    return UserSettings(
        id=user.id,
        email=user.email,
        steam_id=user.steam_id,
        discord_id=user.discord_id,
        threshold_up=float(user.threshold_up),
        threshold_down=float(user.threshold_down),
    )


@router.get("", response_model=UserSettings)
async def get_settings(
    user: User = Depends(get_current_user),
) -> UserSettings:
    return _user_to_schema(user)


@router.put("", response_model=UserSettings)
async def update_settings(
    body: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettings:
    if body.steam_id is not None:
        user.steam_id = body.steam_id
    if body.discord_id is not None:
        user.discord_id = body.discord_id
    if body.threshold_up is not None:
        user.threshold_up = body.threshold_up  # type: ignore[assignment]
    if body.threshold_down is not None:
        user.threshold_down = body.threshold_down  # type: ignore[assignment]

    await db.commit()
    await db.refresh(user)
    return _user_to_schema(user)
