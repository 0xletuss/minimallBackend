from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from models.cart_model import CartModel
from routes.auth_routes import get_current_user

router = APIRouter()
cart_model = CartModel()

# Pydantic models
class AddToCartRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0)
    variant_id: Optional[int] = None

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0)

class CartResponse(BaseModel):
    success: bool
    cart: dict

class MessageResponse(BaseModel):
    success: bool
    message: str

class CartCountResponse(BaseModel):
    success: bool
    count: int

# Routes
@router.post("/add", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    request: AddToCartRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add item to cart"""
    try:
        result = cart_model.add_item(
            user_id=current_user['id'],
            product_id=request.product_id,
            quantity=request.quantity,
            variant_id=request.variant_id
        )
        
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

@router.get("", response_model=CartResponse)
@router.get("/", response_model=CartResponse)
async def get_cart(current_user: dict = Depends(get_current_user)):
    """Get user's cart with all items"""
    try:
        result = cart_model.get_cart(current_user['id'])
        
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

@router.get("/count", response_model=CartCountResponse)
async def get_cart_count(current_user: dict = Depends(get_current_user)):
    """Get total number of items in cart"""
    try:
        count = cart_model.get_cart_count(current_user['id'])
        
        return {
            "success": True,
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/items/{cart_item_id}", response_model=MessageResponse)
async def update_cart_item(
    cart_item_id: int,
    request: UpdateCartItemRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update quantity of a cart item"""
    try:
        result = cart_model.update_item_quantity(
            user_id=current_user['id'],
            cart_item_id=cart_item_id,
            quantity=request.quantity
        )
        
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

@router.delete("/items/{cart_item_id}", response_model=MessageResponse)
async def remove_cart_item(
    cart_item_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove item from cart"""
    try:
        result = cart_model.remove_item(
            user_id=current_user['id'],
            cart_item_id=cart_item_id
        )
        
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

@router.delete("/clear", response_model=MessageResponse)
async def clear_cart(current_user: dict = Depends(get_current_user)):
    """Clear all items from cart"""
    try:
        result = cart_model.clear_cart(current_user['id'])
        
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