from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ahbackend import config
from ahbackend.db import User, UserAuth
from ahbackend.db.operations import update_password
from ahbackend.db.queries import get_user, get_user_auth, get_user_project_roles

router = APIRouter()

# Shared across the whole app: api.py attaches this instance to `app.state` and
# registers slowapi's exception handler. Keyed by client IP.
limiter = Limiter(key_func=get_remote_address)

MIN_PASSWORD_LENGTH = 8
# bcrypt silently truncates the password to 72 bytes before hashing, so two
# passwords that share a 72-byte prefix would verify against the same hash.
# Rejecting longer inputs keeps that truncation from masking a weak suffix.
MAX_PASSWORD_BYTES = 72


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        password=plain_password.encode(encoding="utf-8"),
        hashed_password=hashed.encode(encoding="utf-8"),
    )


# A bcrypt hash of a value no one can supply, used only to spend the same time
# verifying a password when the account (or its auth row) is missing. Without
# it, the login path would skip bcrypt for unknown emails and answer faster,
# turning response latency into a user-enumeration oracle.
_DUMMY_HASH: str = bcrypt.hashpw(
    b"constant-time login placeholder", bcrypt.gensalt()
).decode("utf-8")


def is_valid_credentials(password: str, user_auth: UserAuth | None) -> bool:
    # Always run bcrypt — even for a missing/disabled account — so the response
    # time doesn't reveal whether the email is registered. The boolean checks
    # run only after the (constant-cost) verification.
    hashed = user_auth.hashed_password if user_auth else _DUMMY_HASH
    password_ok = verify_password(password, hashed)
    return password_ok and user_auth is not None and not user_auth.disabled


def validate_password_policy(password: str) -> str | None:
    """Return a reason the password is unacceptable, or None if it's fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"Password must be at most {MAX_PASSWORD_BYTES} bytes long"
    return None


def authenticate_user(username: str, password: str) -> User | None:
    user = get_user(username)
    user_auth = get_user_auth(user.user_id) if user else None
    return user if is_valid_credentials(password, user_auth) else None


async def get_token(
    authorization: Annotated[str | None, Header()] = None,
    auth_token: Annotated[str | None, Cookie()] = None,
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


# These auth dependencies are plain `def`, not `async def`, on purpose: each
# does synchronous SQLite work, and FastAPI runs `def` dependencies in a thread
# instead of on the event loop. As `async def` they blocked the loop on every
# request (jwt.decode is µs and could stay async, but the DB reads cannot).
def get_current_user(
    token: Annotated[str, Depends(get_token)],
) -> User:
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
        raise credentials_exception from None
    else:
        user = get_user(username)
        if user is None:
            raise credentials_exception
        return user


def get_current_user_auth(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserAuth | None:
    """Load the caller's auth row once per request.

    FastAPI caches a dependency's result within a request, so routing every
    auth check (active/admin/superuser/manager) and any route body that needs
    the auth row through this single dependency collapses what used to be 2-4
    ``get_user_auth`` queries per request into one. Returns ``None`` (rather
    than raising) so each consumer keeps its own missing-auth semantics.
    """
    return get_user_auth(current_user.user_id)


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_auth: Annotated[UserAuth | None, Depends(get_current_user_auth)],
) -> User:
    if user_auth and user_auth.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(get_current_user_auth)],
) -> User:
    if not user_auth or not user_auth.is_super_user:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return current_user


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(get_current_user_auth)],
) -> User:
    """Allow users with the can_manage permission flag."""
    if not user_auth or not user_auth.can_manage:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(get_current_user_auth)],
) -> User:
    """Allow users with can_manage permission or a project-level manager
    role."""
    if user_auth and user_auth.can_manage:
        return current_user
    roles = get_user_project_roles(current_user.user_id, project_id)
    if "manager" not in roles:
        raise HTTPException(
            status_code=403, detail="Project manager access required"
        )
    return current_user


def create_access_token(
    data: dict,
    expires_delta: timedelta,
    now: datetime,
    private_key,
    algorithm: str,
):
    to_encode = data.copy()
    expire = now + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, private_key, algorithm=algorithm)


@router.post("/token")
@limiter.limit(config.LOGIN_RATE_LIMIT)
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    # authenticate_user runs bcrypt (~180ms at prod cost) plus two SQLite reads;
    # run it in a thread so it can't block the event loop for every other
    # in-flight request (TICKET-27 makes bcrypt run unconditionally per login).
    user = await run_in_threadpool(
        authenticate_user, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
        now=datetime.now(UTC),
        private_key=config.PRIVATE_KEY,
        algorithm=config.ALGORITHM,
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


@router.post("/change-password")
@limiter.limit(config.CHANGE_PASSWORD_RATE_LIMIT)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(get_current_user_auth)],
) -> None:
    # Both bcrypt calls (verify, then hash-on-update) go through the threadpool
    # so /change-password doesn't block the loop the way /token would.
    if user_auth is None or not await run_in_threadpool(
        verify_password, body.current_password, user_auth.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if body.new_password == body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )
    policy_error = validate_password_policy(body.new_password)
    if policy_error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=policy_error
        )
    await run_in_threadpool(
        update_password, current_user.user_id, body.new_password
    )


@router.post("/logout")
async def logout(response: Response) -> None:
    response.delete_cookie(
        key="auth_token",
        samesite="strict",
        secure=config.COOKIE_SECURE,
    )
