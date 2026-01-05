from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from models.admin_model import AdminModel
from middleware.auth_middleware import get_current_user

router = APIRouter()
admin_model = AdminModel()

class UserStatusUpdate(BaseModel):
    is_active: bool

class SellerApplicationReview(BaseModel):
    status: str  # approved, rejected
    rejection_reason: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class ProductStatusUpdate(BaseModel):
    is_active: bool

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard statistics"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats = admin_model.get_dashboard_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_all_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all users with pagination and filters"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        users = admin_model.get_all_users(page, limit, search, role)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user active status"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = admin_model.update_user_status(user_id, status_update.is_active)
        if result:
            return {"message": "User status updated successfully"}
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/seller-applications")
async def get_seller_applications(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all seller applications"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        applications = admin_model.get_seller_applications(status)
        return applications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/seller-applications/{application_id}")
async def review_seller_application(
    application_id: int,
    review: SellerApplicationReview,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject seller application"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = admin_model.review_seller_application(
            application_id,
            review.status,
            review.rejection_reason,
            current_user['id']
        )
        if result:
            return {"message": f"Application {review.status} successfully"}
        raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_all_orders(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all orders with pagination and filters"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        orders = admin_model.get_all_orders(page, limit, status, search)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}")
async def get_order_details(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed order information"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        order = admin_model.get_order_details(order_id)
        if order:
            return order
        raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update order status"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = admin_model.update_order_status(
            order_id,
            status_update.status,
            status_update.notes,
            current_user['id']
        )
        if result:
            return {"message": "Order status updated successfully"}
        raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products")
async def get_all_products(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all products with pagination and filters"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        products = admin_model.get_all_products(page, limit, search, category_id)
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/products/{product_id}/status")
async def update_product_status(
    product_id: int,
    status_update: ProductStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update product active status"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = admin_model.update_product_status(product_id, status_update.is_active)
        if result:
            return {"message": "Product status updated successfully"}
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a product"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = admin_model.delete_product(product_id)
        if result:
            return {"message": "Product deleted successfully"}
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/revenue")
async def get_revenue_analytics(
    period: str = "monthly",  # daily, weekly, monthly, yearly
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get revenue analytics"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = admin_model.get_revenue_analytics(period, start_date, end_date)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/top-products")
async def get_top_products(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get top selling products"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        products = admin_model.get_top_products(limit)
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/top-sellers")
async def get_top_sellers(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get top sellers by revenue"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        sellers = admin_model.get_top_sellers(limit)
        return sellers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))