"""Seguridad Estila: hash bcrypt, JWT, Fernet para secretos SIFEN (RNF03/RNF04)."""

import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


# --- Passwords (RNF03: bcrypt) ---
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# --- JWT con tenant_id + rol (RF02) ---
def create_access_token(sub: str, tenant_id: str, rol: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MIN)
    payload = {"sub": sub, "tenant_id": tenant_id, "rol": rol, "exp": exp}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


# --- Cifrado simetrico para secretos/certificados por tenant (RNF04) ---
def _get_fernet() -> Fernet:
    digest = hashlib.sha256(settings.MASTER_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("No se pudo descifrar (MASTER_KEY incorrecta)") from e
