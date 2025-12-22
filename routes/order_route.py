from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from models.order_model import OrderModel
from routes.auth_routes import get_current_user
from pydantic import BaseModel

router = APIRouter()
order_model = OrderModel()

# ==================== PYDANTIC MODELS ====================

class OrderStatusUpdate(BaseModel):
    tracking_number: Optional[str] = None

class OrderCancelRequest(BaseModel):
    reason: Optional[str] = "Cancelled by seller"

class OrderStatusPatch(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def verify_seller_access(current_user: dict) -> bool:
    """
    Verify if user has seller access
    Returns True if user is an active seller, False otherwise
    """
    if not current_user:
        return False
    
    is_seller = current_user.get("is_seller", False)
    seller_status = current_user.get("seller_status", "")
    role = current_user.get("role", "")
    
    return (is_seller and seller_status in ["active", "approved"]) or role == "admin"


def validate_status_transition(current_status: str, new_status: str) -> tuple[bool, str]:
    """
    Validate if status transition is allowed
    Returns (is_valid, error_message)
    """
    # Cannot update cancelled orders
    if current_status == 'cancelled':
        return False, "Cannot update cancelled order"
    
    # Cannot update delivered orders except to cancel
    if current_status == 'delivered' and new_status != 'cancelled':
        return False, "Cannot update delivered order"
    
    # Can only cancel pending or processing orders
    if new_status == 'cancelled' and current_status not in ['pending', 'processing']:
        return False, "Order can only be cancelled if pending or processing"
    
    # Valid status flow: pending -> processing -> shipped -> delivered
    status_order = ['pending', 'processing', 'shipped', 'delivered']
    
    if new_status in status_order and current_status in status_order:
        current_idx = status_order.index(current_status)
        new_idx = status_order.index(new_status)
        
        # Allow moving forward or staying same
        if new_idx < current_idx and new_status != 'pending':
            return False, f"Cannot move from {current_status} back to {new_status}"
    
    return True, ""


# ==================== SELLER ORDER ROUTES ====================

@router.get("/seller/orders")
async def get_seller_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query("all", description="Filter by status"),
    date_range: Optional[str] = Query("all", description="Filter by date range"),
    search: Optional[str] = Query("", description="Search term"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all orders containing seller's products with pagination and filters
    """
    try:
        # Verify seller access
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Parse date filter
        date_filter = None
        if date_range == "today":
            date_filter = datetime.now().date()
        elif date_range == "this_week":
            date_filter = datetime.now() - timedelta(days=7)
        elif date_range == "this_month":
            date_filter = datetime.now() - timedelta(days=30)
        elif date_range == "last_week":
            date_filter = datetime.now() - timedelta(days=14)
        
        # Parse status filter
        status_filter = status if status != "all" else None
        search_term = search if search else None
        
        # Get orders
        orders = order_model.get_seller_orders(
            seller_id=seller_id,
            page=page,
            limit=limit,
            status=status_filter,
            date_from=date_filter,
            search_term=search_term
        )
        
        # Get statistics
        stats = order_model.get_seller_order_stats(seller_id)
        
        # Calculate total for pagination
        total_orders = order_model.count_seller_orders(
            seller_id=seller_id,
            status=status_filter,
            date_from=date_filter,
            search_term=search_term
        )
        
        return {
            "success": True,
            "orders": orders,
            "stats": stats,
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_items": total_orders,
                "total_pages": (total_orders + limit - 1) // limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching seller orders: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/seller/orders/{order_id}")
async def get_seller_order_details(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific order (seller's items only)
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Verify access and get order
        order = order_model.get_seller_order_details(order_id, seller_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found or access denied")
        
        # Get status history
        history = order_model.get_order_status_history(order_id)
        order['status_history'] = history
        
        return {
            "success": True,
            "order": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching order details: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch order details")


@router.patch("/seller/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    data: OrderStatusPatch,
    current_user: dict = Depends(get_current_user)
):
    """
    Update order status (generic endpoint for any status change)
    This is the main endpoint used by the frontend
    """
    try:
        # Verify seller access
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        # Verify seller has items in this order
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied - you don't have items in this order")
        
        # Validate status value
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Get current order
        order = order_model.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        current_status = order['status']
        
        # Validate status transition
        is_valid, error_msg = validate_status_transition(current_status, data.status)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Update order status in database
        success = order_model.update_order_status(
            order_id=order_id,
            status=data.status,
            tracking_number=data.tracking_number
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update order status in database")
        
        # Build status history notes
        history_notes = data.notes or f"Status changed to {data.status} by seller"
        if data.tracking_number and data.status == 'shipped':
            history_notes += f" - Tracking: {data.tracking_number}"
        
        # Add to status history
        order_model.add_status_history(
            order_id=order_id,
            status=data.status,
            notes=history_notes,
            created_by=seller_id
        )
        
        # If cancelled, restore inventory
        if data.status == 'cancelled':
            order_model.restore_inventory_for_order(order_id, seller_id)
        
        # Get updated order details
        updated_order = order_model.get_seller_order_details(order_id, seller_id)
        
        return {
            "success": True,
            "message": f"Order status updated to {data.status}",
            "order": updated_order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating order status: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {str(e)}")


@router.put("/seller/orders/{order_id}/process")
async def process_order(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark order as processing (convenience endpoint)
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current order to validate
        order = order_model.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Validate transition
        is_valid, error_msg = validate_status_transition(order['status'], 'processing')
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        success = order_model.update_order_status(order_id, "processing")
        
        if success:
            order_model.add_status_history(
                order_id=order_id,
                status="processing",
                notes=f"Order marked as processing by seller (ID: {seller_id})",
                created_by=seller_id
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
        print(f"❌ Error processing order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process order")


@router.put("/seller/orders/{order_id}/ship")
async def mark_as_shipped(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark order as shipped with optional tracking number
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current order to validate
        order = order_model.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Validate transition
        is_valid, error_msg = validate_status_transition(order['status'], 'shipped')
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        success = order_model.update_order_status(
            order_id=order_id,
            status="shipped",
            tracking_number=data.tracking_number
        )
        
        if success:
            notes = f"Order shipped by seller (ID: {seller_id})"
            if data.tracking_number:
                notes += f" - Tracking: {data.tracking_number}"
                
            order_model.add_status_history(
                order_id=order_id,
                status="shipped",
                notes=notes,
                created_by=seller_id
            )
            
            return {
                "success": True,
                "message": "Order marked as shipped",
                "tracking_number": data.tracking_number
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update order")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error marking as shipped: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark as shipped")


@router.put("/seller/orders/{order_id}/deliver")
async def mark_as_delivered(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark order as delivered
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current order to validate
        order = order_model.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Validate transition
        is_valid, error_msg = validate_status_transition(order['status'], 'delivered')
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        success = order_model.update_order_status(order_id, "delivered")
        
        if success:
            order_model.add_status_history(
                order_id=order_id,
                status="delivered",
                notes=f"Order marked as delivered by seller (ID: {seller_id})",
                created_by=seller_id
            )
            
            return {
                "success": True,
                "message": "Order marked as delivered"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update order")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error marking as delivered: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark as delivered")


@router.put("/seller/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    data: OrderCancelRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an order (only if pending or processing)
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        
        if not order_model.seller_has_items_in_order(order_id, seller_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get and validate order
        order = order_model.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Validate transition
        is_valid, error_msg = validate_status_transition(order['status'], 'cancelled')
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        success = order_model.update_order_status(order_id, "cancelled")
        
        if success:
            order_model.add_status_history(
                order_id=order_id,
                status="cancelled",
                notes=f"Cancelled by seller (ID: {seller_id}) - Reason: {data.reason}",
                created_by=seller_id
            )
            
            # Restore inventory
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
        print(f"❌ Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")


@router.get("/seller/orders/stats/summary")
async def get_order_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get seller order statistics and revenue data
    """
    try:
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
        print(f"❌ Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/seller/revenue")
async def get_seller_revenue(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get seller revenue data for specified period
    """
    try:
        if not verify_seller_access(current_user):
            raise HTTPException(status_code=403, detail="Seller access required")
        
        seller_id = current_user["id"]
        revenue_data = order_model.get_seller_revenue_data(seller_id, days=days)
        
        return {
            "success": True,
            "revenue": revenue_data,
            "period_days": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching revenue: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch revenue data")


# ==================== CUSTOMER ORDER ROUTES ====================

@router.get("/customer/orders")
async def get_customer_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer's orders with pagination
    """
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
        print(f"❌ Error fetching customer orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch orders")


@router.get("/customer/orders/{order_id}")
async def get_customer_order_details(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer order details
    """
    try:
        user_id = current_user["id"]
        
        order = order_model.get_customer_order_details(order_id, user_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get status history
        history = order_model.get_order_status_history(order_id)
        order['status_history'] = history
        
        return {
            "success": True,
            "order": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching order details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch order details")


@router.get("/orders/{order_id}/status-history")
async def get_order_status_history(
    order_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get order status history (accessible by customer or seller)
    """
    try:
        user_id = current_user["id"]
        
        # Verify user has access to this order
        order = order_model.get_order_by_id(order_id)
        
        # Check if user is the customer
        is_customer = order and order.get("user_id") == user_id
        
        # Check if user is seller with items in order
        is_seller = order_model.seller_has_items_in_order(order_id, user_id)
        
        if not (is_customer or is_seller):
            raise HTTPException(status_code=403, detail="Access denied")
        
        history = order_model.get_order_status_history(order_id)
        
        return {
            "success": True,
            "history": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching status history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch status history")