from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
import os
from utils.cloudinary_utils import CloudinaryService

router = APIRouter()
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


class Base64ImageUpload(BaseModel):
    image_data: str  # Base64 encoded image
    folder: str = "products"
    public_id: Optional[str] = None


class ImageUploadResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    secure_url: Optional[str] = None
    public_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


# ==================== IMAGE UPLOAD ROUTES ====================

@router.post("/upload/product-image", response_model=ImageUploadResponse)
async def upload_product_image(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """
    Upload product image (multipart/form-data)
    Accepts: JPG, PNG, WEBP, GIF
    Max size: 10MB
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: JPG, PNG, WEBP, GIF"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Check file size (max 10MB)
        if len(file_data) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 10MB"
            )
        
        # Upload to Cloudinary
        result = CloudinaryService.upload_image(
            file_data,
            folder="products"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Upload failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/upload/product-image-base64", response_model=ImageUploadResponse)
async def upload_product_image_base64(
    image_upload: Base64ImageUpload,
    user_id: int = Depends(get_current_user_id)
):
    """
    Upload product image from base64 string
    """
    try:
        result = CloudinaryService.upload_base64_image(
            image_upload.image_data,
            folder=image_upload.folder,
            public_id=image_upload.public_id
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Upload failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/upload/profile-image", response_model=ImageUploadResponse)
async def upload_profile_image(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """Upload user profile image"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: JPG, PNG, WEBP"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Check file size (max 5MB)
        if len(file_data) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 5MB"
            )
        
        # Upload to Cloudinary
        result = CloudinaryService.upload_image(
            file_data,
            folder="profiles",
            public_id=f"user_{user_id}"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Upload failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/upload/store-logo", response_model=ImageUploadResponse)
async def upload_store_logo(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """Upload seller store logo"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: JPG, PNG, WEBP"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Check file size (max 5MB)
        if len(file_data) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 5MB"
            )
        
        # Upload to Cloudinary
        result = CloudinaryService.upload_image(
            file_data,
            folder="stores/logos",
            public_id=f"seller_{user_id}"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Upload failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/upload/store-banner", response_model=ImageUploadResponse)
async def upload_store_banner(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """Upload seller store banner"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: JPG, PNG, WEBP"
            )
        
        # Read file data
        file_data = await file.read()
        
        # Check file size (max 10MB)
        if len(file_data) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size: 10MB"
            )
        
        # Upload to Cloudinary
        result = CloudinaryService.upload_image(
            file_data,
            folder="stores/banners",
            public_id=f"seller_{user_id}_banner"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Upload failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.delete("/upload/delete/{public_id:path}")
async def delete_image(
    public_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """Delete image from Cloudinary"""
    try:
        result = CloudinaryService.delete_image(public_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Delete failed")
            )
        
        return {"success": True, "message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )