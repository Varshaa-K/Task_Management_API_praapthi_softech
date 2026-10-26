import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key or len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be set to a value of at least 32 characters")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key or len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be set to a value of at least 32 characters")
    payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise jwt.InvalidTokenError("Invalid token subject")
    return int(subject)
