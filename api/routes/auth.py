import os
import sys
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.user import User
from infra.database.models.refresh_token import RefreshToken
from infra.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from api.dependencies import get_db, get_current_active_user
from api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    try:
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        password_hash = hash_password(request.password)
        
        user = User(
            email=request.email,
            name=request.name,
            password_hash=password_hash,
            is_active=True,
            is_verified=False
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token_str = create_refresh_token(data={"sub": str(user.id)})
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=7),
            revoked=False
        )
        db.add(refresh_token)
        db.commit()
        
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token_str
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login and get access tokens."""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    print(f"[AUTH] Login successful for user_id={user.id}, email={user.email}")
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})
    print(f"[AUTH] Tokens created: access_token (first 20 chars: {access_token[:20]}...), refresh_token (first 20 chars: {refresh_token_str[:20]}...)")
    
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=7),
        revoked=False
    )
    db.add(refresh_token)
    db.commit()
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    print(f"[AUTH] Refresh token request received (token first 20 chars: {request.refresh_token[:20]}...)")
    try:
        payload = decode_token(request.refresh_token)
        user_id: int = int(payload.get("sub"))
        token_type: str = payload.get("type")
        
        print(f"[AUTH] Refresh token decoded: user_id={user_id}, token_type={token_type}")
        
        if user_id is None or token_type != "refresh":
            print(f"[AUTH] Refresh token validation failed: user_id={user_id}, token_type={token_type} (expected 'refresh')")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except ValueError as e:
        print(f"[AUTH] ValueError during refresh token decode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token,
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).first()
    
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token
    )


@router.post("/logout")
async def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Revoke a refresh token (logout)."""
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token,
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    ).first()
    
    if stored_token:
        stored_token.revoked = True
        db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponse.model_validate(current_user)

