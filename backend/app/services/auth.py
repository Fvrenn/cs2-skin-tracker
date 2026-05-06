from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


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
