from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
from models.product_model import ProductModel

router = APIRouter(prefix="/api/products", tags=["products"])
product_model = ProductModel()

# Pydantic models for responses
class ProductImage(BaseModel):
    id: int
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool
    display_order: int

class ProductVariant(BaseModel):
    id: int
    variant_name: str
    variant_value: str
    price_modifier: float
    sku: Optional[str] = None
    quantity_in_stock: int
    is_active: bool

class ProductListItem(BaseModel):
    id: int
    name: str
    slug: str
    short_description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    category_name: str
    category_slug: str
    primary_image: Optional[str] = None
    is_featured: bool
    rating_average: float
    rating_count: int
    quantity_in_stock: int

class ProductDetail(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    category_id: int
    category_name: str
    category_slug: str
    sku: Optional[str] = None
    quantity_in_stock: int
    is_featured: bool
    rating_average: float
    rating_count: int
    view_count: int
    images: List[dict]
    variants: List[dict]
    tags: List[str]

class ProductListResponse(BaseModel):
    success: bool
    products: List[dict]
    total: int
    limit: int
    offset: int

class ProductResponse(BaseModel):
    success: bool
    product: dict

class CategoryResponse(BaseModel):
    success: bool
    categories: List[dict]

class CategoryDetailResponse(BaseModel):
    success: bool
    category: dict

# Routes
@router.get("/products", response_model=ProductListResponse)
async def get_products(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: Optional[int] = Query(None),
    is_featured: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get all products with optional filters
    
    - **limit**: Number of products to return (max 100)
    - **offset**: Number of products to skip
    - **category_id**: Filter by category ID
    - **is_featured**: Filter featured products only
    - **search**: Search in product name and description
    """
    try:
        result = product_model.get_all_products(
            limit=limit,
            offset=offset,
            category_id=category_id,
            is_featured=is_featured,
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

@router.get("/products/featured", response_model=ProductListResponse)
async def get_featured_products(limit: int = Query(8, ge=1, le=50)):
    """Get featured products"""
    try:
        result = product_model.get_featured_products(limit=limit)
        
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

@router.get("/products/search", response_model=ProductListResponse)
async def search_products(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search products by name or description
    
    - **q**: Search query (minimum 2 characters)
    - **limit**: Number of results to return
    """
    try:
        result = product_model.search_products(search_term=q, limit=limit)
        
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

@router.get("/products/tag/{tag_name}", response_model=dict)
async def get_products_by_tag(
    tag_name: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get products by tag
    
    - **tag_name**: Tag to filter by (e.g., 'bestseller', 'trending')
    - **limit**: Number of products to return
    """
    try:
        result = product_model.get_products_by_tag(tag_name=tag_name, limit=limit)
        
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

@router.get("/products/id/{product_id}", response_model=ProductResponse)
async def get_product_by_id(product_id: int):
    """
    Get product details by ID
    
    - **product_id**: Product ID
    """
    try:
        result = product_model.get_product_by_id(product_id)
        
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

@router.get("/products/{slug}", response_model=ProductResponse)
async def get_product_by_slug(slug: str):
    """
    Get product details by slug
    
    - **slug**: Product slug (URL-friendly identifier)
    """
    try:
        result = product_model.get_product_by_slug(slug)
        
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

@router.get("/categories", response_model=CategoryResponse)
async def get_categories():
    """Get all active categories with product counts"""
    try:
        result = product_model.get_all_categories()
        
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

@router.get("/categories/{slug}", response_model=CategoryDetailResponse)
async def get_category_by_slug(slug: str):
    """
    Get category details by slug
    
    - **slug**: Category slug (e.g., 'shoes', 'outerwear')
    """
    try:
        result = product_model.get_category_by_slug(slug)
        
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