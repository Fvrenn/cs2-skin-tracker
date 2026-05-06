from uuid import UUID

from pydantic import BaseModel


class UserSettings(BaseModel):
    id: UUID
    email: str
    steam_id: str | None
    discord_id: str | None
    threshold_up: float
    threshold_down: float


class UserSettingsUpdate(BaseModel):
    steam_id: str | None = None
    discord_id: str | None = None
    threshold_up: float | None = None
    threshold_down: float | None = None
