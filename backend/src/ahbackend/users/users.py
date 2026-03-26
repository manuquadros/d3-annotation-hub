from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import bcrypt
import jwt
from ahbackend import config, db
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        password=plain_password.encode(encoding="utf-8"),
        hashed_password=hashed.encode(encoding="utf-8"),
    )


def authenticate_user(username: str, password: str) -> db.User | None:
    user = db.get_user(username)
    user_auth = db.get_user_auth(user.user_id) if user else None
    if user_auth and verify_password(password, user_auth.hashed_password):
        if user_auth.disabled:
            return None
        return db.get_user(username)
    return None


async def get_token(
    authorization: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Cookie()] = None,
) -> str:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    if auth_token:
        return auth_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
) -> db.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, config.PUBLIC_KEY, algorithms=[config.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    else:
        user = db.get_user(username)
        if user is None:
            raise credentials_exception
        return user


async def get_current_active_user(
    current_user: Annotated[db.User, Depends(get_current_user)],
) -> db.User:
    user_auth = db.get_user_auth(current_user.user_id)
    if user_auth and user_auth.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: Annotated[db.User, Depends(get_current_active_user)],
) -> db.User:
    user_auth = db.get_user_auth(current_user.user_id)
    if not user_auth or user_auth.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.PRIVATE_KEY, algorithm=config.ALGORITHM
    )
    return encoded_jwt


@router.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        samesite="strict",
        max_age=int(access_token_expires.total_seconds()),
        secure=config.COOKIE_SECURE,
    )
    return Token(access_token=access_token, token_type="bearer")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[db.User, Depends(get_current_active_user)],
) -> None:
    user_auth = db.get_user_auth(current_user.user_id)
    if user_auth is None or not verify_password(body.current_password, user_auth.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    db.update_password(current_user.user_id, body.new_password)


@router.post("/admin/reset-password/{username}")
async def reset_password(
    username: str,
    body: ResetPasswordRequest,
    _: Annotated[db.User, Depends(get_current_admin_user)],
) -> None:
    user = db.get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.update_password(user.user_id, body.new_password)


@router.post("/logout")
async def logout(response: Response) -> None:
    response.delete_cookie(
        key="auth_token",
        samesite="strict",
        secure=config.COOKIE_SECURE,
    )
