"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm]
        )
        return payload
    except JWTError as e:
        import logging
        logging.error(f"JWT decode error: {e}")
        return None


class TokenData:
    """Token payload data"""
    def __init__(self, user_id: int, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role


async def get_current_user_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current user from token"""
    import logging
    logging.info(f"Received token: {token[:50]}..." if len(token) > 50 else f"Received token: {token}")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    logging.info(f"Decoded payload: {payload}")
    if payload is None:
        logging.error("Token decode failed - payload is None")
        raise credentials_exception
    
    # sub is stored as string, convert back to int
    sub = payload.get("sub")
    user_id: int = int(sub) if sub else None
    username: str = payload.get("username")
    role: str = payload.get("role", "user")
    
    if user_id is None or username is None:
        logging.error(f"Missing user_id or username: user_id={user_id}, username={username}")
        raise credentials_exception
    
    return TokenData(user_id=user_id, username=username, role=role)


async def require_admin(current_user: TokenData = Depends(get_current_user_token)) -> TokenData:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
