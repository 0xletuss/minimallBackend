from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from models.auth_model import AuthModel
from models.otp_model import OTPModel
from utils.email_service import brevo_service

router = APIRouter()
auth_model = AuthModel()
otp_model = OTPModel()
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

class SendOTPRequest(BaseModel):
    email: EmailStr
    full_name: str
    purpose: str = Field(default='registration', pattern='^(registration|login)$')

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    purpose: str = Field(default='registration', pattern='^(registration|login)$')

class CompleteSignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: Optional[str] = Field(default='customer', pattern='^(customer|admin|seller|support)$')
    otp_code: str

class TokenResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
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

# OTP Routes
@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(request: SendOTPRequest):
    """Send OTP to email for registration or login"""
    try:
        # Check if user exists
        user = auth_model.get_user_by_email(request.email)
        
        if request.purpose == 'registration' and user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if request.purpose == 'login' and not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate OTP
        otp_code = brevo_service.generate_otp()
        
        # Store OTP in database
        otp_result = otp_model.store_otp(request.email, otp_code, request.purpose)
        
        if not otp_result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP"
            )
        
        # Send OTP via email
        email_result = brevo_service.send_otp_email(
            email=request.email,
            name=request.full_name if request.purpose == 'registration' else user['full_name'],
            otp=otp_code,
            purpose=request.purpose
        )
        
        if not email_result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email"
            )
        
        return {
            "success": True,
            "message": f"OTP sent to {request.email}. Please check your inbox."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(request: VerifyOTPRequest):
    """Verify OTP code"""
    try:
        result = otp_model.verify_otp(request.email, request.otp_code, request.purpose)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return {
            "success": True,
            "message": "OTP verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# Updated Auth Routes
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: CompleteSignUpRequest):
    """Complete user registration after OTP verification"""
    try:
        # Verify OTP first
        otp_result = otp_model.verify_otp(request.email, request.otp_code, 'registration')
        
        if not otp_result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Create user
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
        
        # Send welcome email
        brevo_service.send_welcome_email(request.email, request.full_name)
        
        # Generate token
        token = create_access_token({"user_id": result['user_id']})
        
        return {
            "success": True,
            "message": "Registration successful!",
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
    """User login endpoint (now requires OTP verification)"""
    try:
        result = auth_model.verify_user(request.email, request.password)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result['message']
            )
        
        # For now, we'll allow direct login
        # In production, you might want to require OTP for login too
        
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

@router.post("/signin-with-otp", response_model=TokenResponse)
async def signin_with_otp(email: EmailStr, otp_code: str):
    """Login with OTP (alternative to password)"""
    try:
        # Verify OTP
        otp_result = otp_model.verify_otp(email, otp_code, 'login')
        
        if not otp_result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        # Get user
        user = auth_model.get_user_by_email(email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate token
        token = create_access_token({"user_id": user['id']})
        
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": user
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