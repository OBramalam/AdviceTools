from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from infra.database import SessionLocal
from infra.database.models.user import User
from infra.auth.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_db() -> Generator[Session, None, None]:
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return current user."""
    print(f"[AUTH] get_current_user called with token (first 20 chars: {token[:20]}...)")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id: int = int(payload.get("sub"))
        token_type: str = payload.get("type")
        
        print(f"[AUTH] Token payload extracted: user_id={user_id}, token_type={token_type}")
        
        if user_id is None or token_type != "access":
            print(f"[AUTH] Token validation failed: user_id={user_id}, token_type={token_type} (expected 'access')")
            raise credentials_exception
    except ValueError as e:
        print(f"[AUTH] ValueError during token decode: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        print(f"[AUTH] User not found for user_id={user_id}")
        raise credentials_exception
    
    print(f"[AUTH] User authenticated successfully: user_id={user.id}, email={user.email}")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active (not disabled/deleted)."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    return current_user

