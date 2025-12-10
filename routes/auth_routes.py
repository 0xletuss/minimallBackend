from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from models.auth_model import AuthModel

router = APIRouter()
auth_model = AuthModel()
security = HTTPBearer()

# Configuration
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Pydantic models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: Optional[str] = Field(default='customer', pattern='^(customer|admin|seller|support)$')

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    success: bool
    message: str
    token: str
    user_id: Optional[int] = None
    user: Optional[dict] = None

class UserResponse(BaseModel):
    success: bool
    user: dict

class MessageResponse(BaseModel):
    success: bool
    message: str

# JWT Functions
def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user = auth_model.get_user_by_id(user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# Routes
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest):
    """User registration endpoint"""
    try:
        result = auth_model.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            phone=request.phone,
            role=request.role
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        # Generate token
        token = create_access_token({"user_id": result['user_id']})
        
        return {
            "success": True,
            "message": result['message'],
            "token": token,
            "user_id": result['user_id']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/signin", response_model=TokenResponse)
async def signin(request: SignInRequest):
    """User login endpoint"""
    try:
        result = auth_model.verify_user(request.email, request.password)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result['message']
            )
        
        # Generate token
        token = create_access_token({"user_id": result['user']['id']})
        
        return {
            "success": True,
            "message": result['message'],
            "token": token,
            "user": result['user']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile (protected route)"""
    return {
        "success": True,
        "user": current_user
    }

@router.get("/verify-token", response_model=MessageResponse)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify if token is valid (protected route)"""
    return {
        "success": True,
        "message": "Token is valid"
    }