from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from models.order_model import OrderModel
from routes.auth_routes import get_current_user  # Import from auth_routes
from pydantic import BaseModel

router = APIRouter()
order_model = OrderModel()

# Pydantic models for request/response
class OrderStatusUpdate(BaseModel):
    tracking_number: Optional[str] = None

class OrderCancelRequest(BaseModel):
    reason: Optional[str] = "Cancelled by seller"


# Helper function to verify seller access
def verify_seller_access(current_user: dict) -> bool:
    """
    Verify if user has seller access
    Returns True if user is an active seller, False otherwise
    """
    if not current_user:
        return False
    
    # Check if user is marked as seller
    is_seller = current_user.get("is_seller", False)
    
    # Check seller status (should be 'active' or 'approved')
    seller_status = current_user.get("seller_status", "")
    
    # Admin role should also have seller access
    role = current_user.get("role", "")
    
    return (is_seller and seller_status in ["active", "approved"]) or role == "admin"


# ==================== SELLER ORDER ROUTES ====================

@router.get("/seller/orders")
async def get_seller_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query("all"),
    date_range: Optional[str] = Query("all"),
    search: Optional[str] = Query(""),
    current_user: dict = Depends(get_current_user)
):
    """Get all orders containing seller's products"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Calculate date filter
        date_filter = None
        if date_range == "today":
            date_filter = datetime.now().date()
        elif date_range == "this_week":
            date_filter = datetime.now() - timedelta(days=7)
        elif date_range == "this_month":
            date_filter = datetime.now() - timedelta(days=30)
        elif date_range == "last_week":
            date_filter = datetime.now() - timedelta(days=14)
        
        # Get orders
        orders = order_model.get_seller_orders(
            seller_id=seller_id,
            page=page,
            limit=limit,
            status=status if status != "all" else None,
            date_from=date_filter,
            search_term=search
        )
        
        # Get order statistics
        stats = order_model.get_seller_order_stats(seller_id)
        
        # Calculate pagination
        total_orders = order_model.count_seller_orders(
            seller_id=seller_id,
            status=status if status != "all" else None,
            date_from=date_filter,
            search_term=search
        )
        
        pagination = {
            "current_page": page,
            "per_page": limit,
            "total_items": total_orders,
            "total_pages": (total_orders + limit - 1) // limit
        }
        
        return {
            "success": True,
            "orders": orders,
            "stats": stats,
            "pagination": pagination
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching seller orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/seller/orders/{order_id}")
async def get_seller_order_details(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific order"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Get order with seller's items only
        order = order_model.get_seller_order_details(order_id, seller_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found or access denied")
        
        return {
            "success": True,
            "order": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching order details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch order details")


@router.put("/seller/orders/{order_id}/process")
async def process_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Mark order as processing"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Verify seller has items in this order
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update order status
        success = order_model.update_order_status(order_id, "processing")
        
        if success:
            # Add to status history
            order_model.add_status_history(
                order_id=order_id,
                status="processing",
                notes=f"Order processed by seller (ID: {seller_id})"
            )
            
            return {
                "success": True,
                "message": "Order marked as processing"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update order")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process order")


@router.put("/seller/orders/{order_id}/ship")
async def mark_as_shipped(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Mark order as shipped"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Verify seller has items in this order
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update order status
        success = order_model.update_order_status(
            order_id=order_id,
            status="shipped",
            tracking_number=data.tracking_number
        )
        
        if success:
            # Add to status history
            notes = f"Order shipped by seller (ID: {seller_id})"
            if data.tracking_number:
                notes += f" - Tracking: {data.tracking_number}"
                
            order_model.add_status_history(
                order_id=order_id,
                status="shipped",
                notes=notes
            )
            
            return {
                "success": True,
                "message": "Order marked as shipped"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update order")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error marking as shipped: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark as shipped")


@router.put("/seller/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    data: OrderCancelRequest,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an order"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Verify seller has items in this order
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if order can be cancelled (only pending or processing)
        order = order_model.get_order_by_id(order_id)
        if order["status"] not in ["pending", "processing"]:
            raise HTTPException(
                status_code=400, 
                detail="Order cannot be cancelled at this stage"
            )
        
        # Update order status
        success = order_model.update_order_status(order_id, "cancelled")
        
        if success:
            # Add to status history
            order_model.add_status_history(
                order_id=order_id,
                status="cancelled",
                notes=f"Cancelled by seller (ID: {seller_id}) - Reason: {data.reason}"
            )
            
            # Restore inventory if needed
            order_model.restore_inventory_for_order(order_id, seller_id)
            
            return {
                "success": True,
                "message": "Order cancelled successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel order")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")


@router.get("/seller/orders/stats/summary")
async def get_order_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get seller order statistics"""
    try:
        # Verify user is a seller
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        stats = order_model.get_seller_order_stats(seller_id)
        revenue_data = order_model.get_seller_revenue_data(seller_id, days=30)
        
        return {
            "success": True,
            "stats": stats,
            "revenue": revenue_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


# ==================== CUSTOMER ORDER ROUTES ====================

@router.get("/customer/orders")
async def get_customer_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get customer's orders"""
    try:
        user_id = current_user["id"]
        
        orders = order_model.get_customer_orders(
            user_id=user_id,
            page=page,
            limit=limit,
            status=status
        )
        
        total = order_model.count_customer_orders(user_id, status)
        
        return {
            "success": True,
            "orders": orders,
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_items": total,
                "total_pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        print(f"Error fetching customer orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/customer/orders/{order_id}")
async def get_customer_order_details(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get customer order details"""
    try:
        user_id = current_user["id"]
        
        order = order_model.get_customer_order_details(order_id, user_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "success": True,
            "order": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching order details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch order details")


@router.get("/orders/{order_id}/status-history")
async def get_order_status_history(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get order status history"""
    try:
        user_id = current_user["id"]
        
        # Verify user has access to this order
        order = order_model.get_order_by_id(order_id)
        if not order or order["user_id"] != user_id:
            # Check if user is seller with items in order
            if not order_model.seller_has_items_in_order(order_id, user_id):
                raise HTTPException(status_code=403, detail="Access denied")
        
        history = order_model.get_order_status_history(order_id)
        
        return {
            "success": True,
            "history": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching status history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch status history")