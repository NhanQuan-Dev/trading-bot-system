"""JWT Authentication utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import os
import uuid

# JWT Settings from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenPayload:
    """JWT token payload."""
    
    def __init__(
        self,
        sub: str,  # subject (user_id)
        exp: datetime,  # expiration time
        iat: datetime,  # issued at
        jti: str,  # JWT ID
        token_type: str = "access",  # access or refresh
    ):
        self.sub = sub
        self.exp = exp
        self.iat = iat
        self.jti = jti
        self.token_type = token_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JWT encoding."""
        return {
            "sub": self.sub,
            "exp": int(self.exp.timestamp()),
            "iat": int(self.iat.timestamp()),
            "jti": self.jti,
            "type": self.token_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create from dictionary."""
        return cls(
            sub=data["sub"],
            exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(data["iat"], tz=timezone.utc),
            jti=data["jti"],
            token_type=data.get("type", "access"),
        )


def create_access_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: User UUID
        expires_delta: Token expiration time delta
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = TokenPayload(
        sub=str(user_id),
        exp=expire,
        iat=now,
        jti=str(uuid.uuid4()),
        token_type="access",
    )
    
    encoded_jwt = jwt.encode(payload.to_dict(), SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt


def create_refresh_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token.
    
    Args:
        user_id: User UUID
        expires_delta: Token expiration time delta
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = TokenPayload(
        sub=str(user_id),
        exp=expire,
        iat=now,
        jti=str(uuid.uuid4()),
        token_type="refresh",
    )
    
    encoded_jwt = jwt.encode(payload.to_dict(), SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenPayload object
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload_dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = TokenPayload.from_dict(payload_dict)
        
        # Check if token is expired
        if payload.exp < datetime.now(timezone.utc):
            raise JWTError("Token has expired")
        
        return payload
    
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


def verify_access_token(token: str) -> uuid.UUID:
    """
    Verify access token and extract user ID.
    
    Args:
        token: JWT access token string
    
    Returns:
        User UUID
    
    Raises:
        JWTError: If token is invalid or not an access token
    """
    payload = decode_token(token)
    
    if payload.token_type != "access":
        raise JWTError("Token is not an access token")
    
    return uuid.UUID(payload.sub)


def verify_refresh_token(token: str) -> uuid.UUID:
    """
    Verify refresh token and extract user ID.
    
    Args:
        token: JWT refresh token string
    
    Returns:
        User UUID
    
    Raises:
        JWTError: If token is invalid or not a refresh token
    """
    payload = decode_token(token)
    
    if payload.token_type != "refresh":
        raise JWTError("Token is not a refresh token")
    
    return uuid.UUID(payload.sub)


class TokenPair:
    """Access and refresh token pair."""
    
    def __init__(self, access_token: str, refresh_token: str, token_type: str = "Bearer"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
        }


def create_token_pair(user_id: uuid.UUID) -> TokenPair:
    """
    Create access and refresh token pair.
    
    Args:
        user_id: User UUID
    
    Returns:
        TokenPair object
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )
