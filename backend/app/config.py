from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str
    SECRET_KEY: str
    BETTER_AUTH_SECRET: str = ""
    DEBUG: bool = False

    CSFLOAT_API_KEY: str = ""
    SKINPORT_CLIENT_ID: str = ""
    SKINPORT_CLIENT_SECRET: str = ""
    STEAM_API_KEY: str = ""
    STEAM_LOGIN_SECURE: str = ""

    DISCORD_BOT_TOKEN: str = ""

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3001"]


settings = Settings()
