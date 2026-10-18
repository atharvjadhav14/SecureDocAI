
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

# Set a private secret in your environment before running the API.
SECRET_KEY = os.environ.get("SECUREDOC_JWT_SECRET")

if not SECRET_KEY:
    raise RuntimeError(
        "SECUREDOC_JWT_SECRET is missing. "
        "Set it in the VS Code integrated terminal before starting the API."
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_user_id_from_token(token: str) -> int:
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    subject = payload.get("sub")

    if not subject or not subject.isdigit():
        raise ValueError("Invalid user identity in token")

    return int(subject)
