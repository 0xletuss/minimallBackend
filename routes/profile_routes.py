from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from jose import JWTError, jwt
import os

from models.profile_models import (
    ProfileModel,
    ProfileUpdate, ProfileResponse, ProfileDashboardResponse,
    SellerApplicationCreate, SellerApplicationResponse,
    SellerProfileUpdate, SellerProfileResponse,
    UserStatistics, UserCouponResponse,
    RecentTransactionsResponse
)

router = APIRouter()
profile_model = ProfileModel()
security = HTTPBearer()

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Dependency to get current authenticated user ID"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return user_id
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# ==================== PROFILE ENDPOINTS ====================

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user_id: int = Depends(get_current_user_id)):
    """Get current user's profile"""
    try:
        result = profile_model.get_user_profile(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    user_id: int = Depends(get_current_user_id)
):
    """Update user profile"""
    try:
        # Use exclude_none instead of exclude_unset to allow explicit null values
        result = profile_model.update_user_profile(
            user_id, 
            profile_data.dict(exclude_unset=True)
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/profile/dashboard", response_model=ProfileDashboardResponse)
async def get_profile_dashboard(user_id: int = Depends(get_current_user_id)):
    """Get complete profile dashboard with statistics and transactions"""
    try:
        result = profile_model.get_profile_dashboard(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/profile/statistics", response_model=UserStatistics)
async def get_user_statistics(user_id: int = Depends(get_current_user_id)):
    """Get user statistics"""
    try:
        result = profile_model.get_user_statistics(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/profile/transactions", response_model=RecentTransactionsResponse)
async def get_recent_transactions(
    limit: int = 10,
    user_id: int = Depends(get_current_user_id)
):
    """Get recent transactions"""
    try:
        result = profile_model.get_recent_transactions(user_id, limit)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/coupons", response_model=List[UserCouponResponse])
async def get_user_coupons(user_id: int = Depends(get_current_user_id)):
    """Get user's available coupons"""
    try:
        result = profile_model.get_user_coupons(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ==================== SELLER APPLICATION ENDPOINTS ====================

@router.post("/seller/apply", response_model=SellerApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_become_seller(
    application: SellerApplicationCreate,
    user_id: int = Depends(get_current_user_id)
):
    """Submit application to become a seller"""
    try:
        application_data = {
            'store_name': application.store_name,
            'business_type': application.business_type.value,
            'business_description': application.business_description,
            'id_document_url': application.id_document_url,
            'business_document_url': application.business_document_url
        }
        
        result = profile_model.create_seller_application(user_id, application_data)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/seller/application/status", response_model=SellerApplicationResponse)
async def get_seller_application_status(user_id: int = Depends(get_current_user_id)):
    """Check seller application status"""
    try:
        result = profile_model.get_seller_application_status(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ==================== SELLER PROFILE ENDPOINTS ====================

@router.get("/seller/profile", response_model=SellerProfileResponse)
async def get_seller_profile(user_id: int = Depends(get_current_user_id)):
    """Get seller profile - auto-creates if missing"""
    try:
        result = profile_model.get_seller_profile(user_id)
        
        if not result['success']:
            status_code = (
                status.HTTP_403_FORBIDDEN 
                if 'not a seller' in result['message'].lower() 
                else status.HTTP_404_NOT_FOUND
            )
            raise HTTPException(
                status_code=status_code,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/seller/profile/create", response_model=SellerProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_seller_profile(user_id: int = Depends(get_current_user_id)):
    """
    Create seller profile from approved application
    Emergency endpoint for users whose profile wasn't created automatically
    """
    try:
        result = profile_model.create_seller_profile_from_application(user_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/seller/profile", response_model=SellerProfileResponse)
async def update_seller_profile(
    profile_data: SellerProfileUpdate,
    user_id: int = Depends(get_current_user_id)
):
    """Update seller profile"""
    try:
        # Convert enum values to strings
        update_data = {}
        for field, value in profile_data.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value.value if hasattr(value, 'value') else value
        
        result = profile_model.update_seller_profile(user_id, update_data)
        
        if not result['success']:
            status_code = (
                status.HTTP_403_FORBIDDEN 
                if 'not a seller' in result['message'].lower() 
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(
                status_code=status_code,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )