# checkout_routes.py - FastAPI Routes for Checkout

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import sys
sys.path.append('..')
from models.checkout_model import CheckoutModel
from routes.auth_routes import get_current_user
    

router = APIRouter()
checkout_model = CheckoutModel()

# ============================================
# Pydantic Models (Request/Response schemas)
# ============================================

class ShippingInfo(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    address_line1: str = Field(..., min_length=5, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=4, max_length=20)
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Juan Dela Cruz",
                "phone": "09123456789",
                "address_line1": "123 Main Street",
                "address_line2": "Apt 4B",
                "city": "Zamboanga",
                "state": "Zamboanga Peninsula",
                "postal_code": "7000"
            }
        }

class CreateOrderRequest(BaseModel):
    payment_method: str = Field(..., pattern="^(credit_card|debit_card|cash_on_delivery|gcash|paymaya|bank_transfer)$")
    shipping_info: ShippingInfo
    delivery_option: str = Field(default="standard", pattern="^(standard|express|same_day|pickup)$")
    customer_notes: Optional[str] = Field(None, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_method": "gcash",
                "shipping_info": {
                    "full_name": "Juan Dela Cruz",
                    "phone": "09123456789",
                    "address_line1": "123 Main Street",
                    "address_line2": "Apt 4B",
                    "city": "Zamboanga",
                    "state": "Zamboanga Peninsula",
                    "postal_code": "7000"
                },
                "delivery_option": "standard",
                "customer_notes": "Please ring doorbell"
            }
        }

class OrderResponse(BaseModel):
    success: bool
    message: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    total: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping_fee: Optional[float] = None
    marketplace_fee: Optional[float] = None

class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|processing|shipped|delivered|cancelled|refunded)$")
    notes: Optional[str] = Field(None, max_length=1000)

class UpdatePaymentStatusRequest(BaseModel):
    payment_status: str = Field(..., pattern="^(pending|paid|failed|refunded)$")
    transaction_id: Optional[str] = Field(None, max_length=255)

# ============================================
# Explicit OPTIONS handlers (no auth required)
# ============================================

@router.options("/{full_path:path}")
async def options_handler():
    """Handle all OPTIONS requests without authentication"""
    return {"message": "OK"}

# ============================================
# Routes
# ============================================

@router.post("/create", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new order from the user's cart
    
    - Validates cart is not empty
    - Calculates totals (subtotal, tax, shipping, marketplace fee)
    - Creates order and order items
    - Updates product stock
    - Clears cart after successful order
    """
    try:
        user_id = current_user['id']
        
        # Convert shipping info to dict
        shipping_info = request.shipping_info.dict()
        
        # Create order
        result = checkout_model.create_order(
            user_id=user_id,
            payment_method=request.payment_method,
            shipping_info=shipping_info,
            delivery_option=request.delivery_option,
            customer_notes=request.customer_notes
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return OrderResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )

@router.get("/order/{order_id}")
async def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific order
    
    Returns order information including items, pricing, and shipping details
    """
    try:
        user_id = current_user['id']
        
        result = checkout_model.get_order(order_id, user_id)
        
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
            detail=f"Failed to get order: {str(e)}"
        )

@router.get("/orders")
async def get_user_orders(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's order history
    
    Returns list of orders with basic information
    """
    try:
        user_id = current_user['id']
        
        result = checkout_model.get_user_orders(user_id, limit)
        
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
            detail=f"Failed to get orders: {str(e)}"
        )

@router.put("/order/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: UpdateOrderStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update order status (admin/seller only)
    
    Updates order status and records in status history
    """
    try:
        # Check if user has permission (admin/seller)
        if current_user.get('role') not in ['admin', 'seller', 'support']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        result = checkout_model.update_order_status(
            order_id=order_id,
            status=request.status,
            notes=request.notes,
            user_id=current_user['id']
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
            detail=f"Failed to update order status: {str(e)}"
        )

@router.put("/order/{order_id}/payment")
async def update_payment_status(
    order_id: int,
    request: UpdatePaymentStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update payment status
    
    Updates payment status and transaction record
    """
    try:
        # Check if user has permission (admin/seller) or is the order owner
        if current_user.get('role') not in ['admin', 'seller', 'support']:
            # Verify user owns this order
            order_result = checkout_model.get_order(order_id, current_user['id'])
            if not order_result['success']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Order not found or access denied"
                )
        
        result = checkout_model.update_payment_status(
            order_id=order_id,
            payment_status=request.payment_status,
            transaction_id=request.transaction_id
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
            detail=f"Failed to update payment status: {str(e)}"
        )

@router.get("/calculate-total")
async def calculate_order_total(
    delivery_option: str = "standard",
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate order total before checkout
    
    Returns breakdown of costs (subtotal, tax, shipping, marketplace fee, total)
    """
    try:
        user_id = current_user['id']
        
        # Get cart items
        from models.cart_model import CartModel
        cart_model = CartModel()
        cart_result = cart_model.get_cart(user_id)
        
        if not cart_result['success'] or not cart_result['cart']['items']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )
        
        # Calculate totals
        subtotal = cart_result['cart']['total']
        tax = subtotal * 0.12  # 12%
        
        shipping_fees = {
            'standard': 50.00,
            'express': 150.00,
            'same_day': 300.00,
            'pickup': 0.00
        }
        shipping_fee = shipping_fees.get(delivery_option, 50.00)
        
        marketplace_fee = subtotal * 0.02  # 2%
        total = subtotal + tax + shipping_fee + marketplace_fee
        
        return {
            'success': True,
            'subtotal': round(subtotal, 2),
            'tax': round(tax, 2),
            'shipping_fee': round(shipping_fee, 2),
            'marketplace_fee': round(marketplace_fee, 2),
            'total': round(total, 2),
            'item_count': cart_result['cart']['item_count']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate total: {str(e)}"
        )

@router.post("/order/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an order (only if status is pending or processing)
    """
    try:
        user_id = current_user['id']
        
        # Get order to verify ownership and status
        order_result = checkout_model.get_order(order_id, user_id)
        
        if not order_result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = order_result['order']
        
        # Check if order can be cancelled
        if order['status'] not in ['pending', 'processing']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order['status']}"
            )
        
        # Update order status to cancelled
        result = checkout_model.update_order_status(
            order_id=order_id,
            status='cancelled',
            notes=notes or 'Order cancelled by customer',
            user_id=user_id
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return {
            'success': True,
            'message': 'Order cancelled successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )