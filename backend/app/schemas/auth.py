from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str
    steam_id: str | None = None

    @field_validator("email")
    @classmethod
    def email_normalise(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Email invalide")
        return v

    @field_validator("password")
    @classmethod
    def password_min(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mot de passe minimum 6 caractères")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
