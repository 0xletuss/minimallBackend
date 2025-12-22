from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel, Field
from jose import JWTError, jwt
import os
from models.seller_product_model import SellerProductModel

router = APIRouter()
seller_product_model = SellerProductModel()
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

# Pydantic Models
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=3, max_length=255)
    category_id: int
    sku: Optional[str] = Field(None, max_length=100)
    short_description: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    compare_at_price: Optional[float] = Field(None, gt=0)
    quantity_in_stock: int = Field(..., ge=0)
    weight: Optional[float] = Field(None, ge=0)
    is_featured: bool = False
    is_active: bool = True
    image_url: Optional[str] = Field(None, max_length=500)

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=255)
    category_id: Optional[int] = None
    sku: Optional[str] = Field(None, max_length=100)
    short_description: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    compare_at_price: Optional[float] = Field(None, gt=0)
    quantity_in_stock: Optional[int] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=500)

# Routes
@router.get("/seller/products")
async def get_seller_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: str = Query("all", alias="status"),
    search: str = Query(""),
    user_id: int = Depends(get_current_user_id)
):
    """Get seller's products with pagination and filters"""
    try:
        offset = (page - 1) * limit
        
        result = seller_product_model.get_seller_products(
            seller_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            search=search
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/seller/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    user_id: int = Depends(get_current_user_id)
):
    """Create new product"""
    try:
        product_data = product.dict()
        result = seller_product_model.create_product(user_id, product_data)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/seller/products/{product_id}")
async def get_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Get product details (seller must own the product)"""
    try:
        result = seller_product_model.get_seller_product(user_id, product_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/seller/products/{product_id}")
async def update_product(
    product_id: int,
    product: ProductUpdate,
    user_id: int = Depends(get_current_user_id)
):
    """Update product"""
    try:
        product_data = product.dict(exclude_unset=True)
        result = seller_product_model.update_product(user_id, product_id, product_data)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.delete("/seller/products/{product_id}")
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Delete product"""
    try:
        result = seller_product_model.delete_product(user_id, product_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )