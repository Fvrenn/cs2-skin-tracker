from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=_ALGORITHM,
    )


def decode_token(token: str) -> str:
    """Retourne le user_id ou lève JWTError."""
    payload: dict[str, object] = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[_ALGORITHM]
    )
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise JWTError("sub manquant ou invalide")
    return sub
