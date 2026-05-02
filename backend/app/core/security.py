"""
app/core/security.py
Hachage de mot de passe + génération/validation JWT.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
TokenKind = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def hash_refresh_token(token: str) -> str:
    """SHA-256 du refresh token pour stockage sécurisé en base (révocation)."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_token(subject: str, kind: TokenKind = "access") -> str:
    """
    Crée un JWT signé HS256.
    subject : UUID du joueur (str).
    """
    now = datetime.now(UTC)
    expire = now + (
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if kind == "access"
        else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {"sub": subject, "kind": kind, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_kind: TokenKind = "access") -> str:
    """
    Décode et valide un JWT.
    Retourne le sub (UUID joueur).
    Lève ValueError si invalide / expiré / mauvais type.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Token invalide : {exc}") from exc

    if payload.get("kind") != expected_kind:
        raise ValueError(f"Type attendu : {expected_kind!r}, reçu : {payload.get('kind')!r}")

    sub = payload.get("sub")
    if not sub:
        raise ValueError("Token sans sujet (sub).")
    return sub
