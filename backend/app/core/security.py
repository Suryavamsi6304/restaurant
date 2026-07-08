import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models import StaffRole

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


@dataclass
class Principal:
    role: str
    token_subject: str
    token_type: str
    user_id: int | None = None
    customer_id: int | None = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def generate_otp_code() -> str:
    return f'{random.randint(0, 999999):06d}'


def hash_otp(code: str) -> str:
    return sha256(code.encode('utf-8')).hexdigest()


def create_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = payload | {'exp': datetime.utcnow() + expires_delta}
    return jwt.encode(to_encode, settings.secret_key, algorithm='HS256')


def create_access_token(subject: str, role: str, user_id: int | None = None, customer_id: int | None = None) -> str:
    return create_token(
        {
            'sub': subject,
            'role': role,
            'token_type': 'access',
            'user_id': user_id,
            'customer_id': customer_id,
        },
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, role: str, user_id: int | None = None, customer_id: int | None = None) -> str:
    return create_token(
        {
            'sub': subject,
            'role': role,
            'token_type': 'refresh',
            'user_id': user_id,
            'customer_id': customer_id,
        },
        timedelta(minutes=settings.refresh_token_expire_minutes),
    )


def decode_token(token: str) -> Principal:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token.') from exc
    return Principal(
        role=payload['role'],
        token_subject=payload['sub'],
        token_type=payload['token_type'],
        user_id=payload.get('user_id'),
        customer_id=payload.get('customer_id'),
    )


def get_current_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required.')
    principal = decode_token(credentials.credentials)
    if principal.token_type != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Access token required.')
    return principal


def require_roles(*roles: StaffRole | str):
    normalized_roles = {role.value if hasattr(role, 'value') else role for role in roles}

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions.')
        return principal

    return dependency
