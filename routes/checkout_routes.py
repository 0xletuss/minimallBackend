from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from decimal import Decimal
from datetime import datetime, timedelta
import random
import string
import mysql.connector
from mysql.connector import Error

from middleware.auth_middleware import get_current_user
from models.checkout_model import (
    CheckoutRequest, 
    OrderResponse, 
    OrderSummaryResponse, 
    OrderItemResponse
)
from database import get_db

router = APIRouter()

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_str}"

def calculate_shipping_fee(delivery_option: str, subtotal: Decimal) -> Decimal:
    """Calculate shipping fee based on delivery option"""
    fees = {
        "standard": Decimal("50.00"),
        "express": Decimal("150.00"),
        "same_day": Decimal("250.00"),
        "pickup": Decimal("0.00")
    }
    # Free shipping for orders over 5000
    if subtotal >= Decimal("5000.00") and delivery_option != "pickup":
        return Decimal("0.00")
    return fees.get(delivery_option, Decimal("50.00"))

def calculate_estimated_delivery(delivery_option: str) -> datetime:
    """Calculate estimated delivery date"""
    days = {
        "standard": 5,
        "express": 2,
        "same_day": 0,
        "pickup": 1
    }
    return datetime.now() + timedelta(days=days.get(delivery_option, 5))

@router.get("/summary", response_model=OrderSummaryResponse)
async def get_order_summary(current_user: dict = Depends(get_current_user)):
    """Get order summary from cart before checkout"""
    
    connection = None
    cursor = None
    
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        
        # Get user's cart
        cursor.execute(
            "SELECT cart_id FROM cart WHERE user_id = %s LIMIT 1",
            (current_user["id"],)
        )
        cart = cursor.fetchone()
        
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        # Get cart items with product details
        items_query = """
            SELECT 
                ci.product_id,
                ci.variant_id,
                ci.quantity,
                ci.price_at_time,
                p.name as product_name,
                pv.variant_name,
                pv.variant_value,
                pi.image_url
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            LEFT JOIN product_variants pv ON ci.variant_id = pv.id
            LEFT JOIN product_images pi ON p.id = pi.product_id AND pi.is_primary = 1
            WHERE ci.cart_id = %s
        """
        cursor.execute(items_query, (cart['cart_id'],))
        items = cursor.fetchall()
        
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )
        
        # Calculate totals
        subtotal = sum(Decimal(str(item['price_at_time'])) * item['quantity'] for item in items)
        tax = subtotal * Decimal("0.12")  # 12% tax
        marketplace_fee = subtotal * Decimal("0.02")  # 2% marketplace fee
        shipping_fee = Decimal("50.00")  # Default standard shipping
        discount = Decimal("0.00")
        total = subtotal + tax + marketplace_fee + shipping_fee - discount
        
        # Format items
        order_items = [
            OrderItemResponse(
                product_id=item['product_id'],
                variant_id=item['variant_id'],
                quantity=item['quantity'],
                price=Decimal(str(item['price_at_time'])),
                subtotal=Decimal(str(item['price_at_time'])) * item['quantity'],
                product_name=item['product_name'],
                variant_name=item['variant_name'],
                variant_value=item['variant_value'],
                image_url=item['image_url']
            )
            for item in items
        ]
        
        return OrderSummaryResponse(
            subtotal=subtotal,
            tax=tax,
            shipping_fee=shipping_fee,
            marketplace_fee=marketplace_fee,
            discount=discount,
            total=total,
            items=order_items,
            item_count=len(items)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_order_summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order summary: {str(e)}"
        )
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@router.post("/process", response_model=OrderResponse)
async def process_checkout(
    checkout_data: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """Process checkout and create order"""
    
    connection = None
    cursor = None
    
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        
        # Get user's cart
        cursor.execute(
            "SELECT cart_id FROM cart WHERE user_id = %s LIMIT 1",
            (current_user["id"],)
        )
        cart = cursor.fetchone()
        
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        cart_id = cart['cart_id']
        
        # Get cart items
        items_query = """
            SELECT 
                ci.product_id,
                ci.variant_id,
                ci.quantity,
                ci.price_at_time,
                p.name as product_name,
                p.sku,
                pv.variant_name,
                pv.variant_value,
                pv.sku as variant_sku,
                pi.image_url
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            LEFT JOIN product_variants pv ON ci.variant_id = pv.id
            LEFT JOIN product_images pi ON p.id = pi.product_id AND pi.is_primary = 1
            WHERE ci.cart_id = %s
        """
        cursor.execute(items_query, (cart_id,))
        items = cursor.fetchall()
        
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty"
            )
        
        # Calculate order totals
        subtotal = sum(Decimal(str(item['price_at_time'])) * item['quantity'] for item in items)
        tax = subtotal * Decimal("0.12")
        marketplace_fee = subtotal * Decimal("0.02")
        shipping_fee = calculate_shipping_fee(checkout_data.delivery_option.value, subtotal)
        discount = Decimal("0.00")
        total = subtotal + tax + marketplace_fee + shipping_fee - discount
        
        # Generate order number
        order_number = generate_order_number()
        
        # Calculate estimated delivery
        estimated_delivery = calculate_estimated_delivery(checkout_data.delivery_option.value)
        
        # Create order
        order_query = """
            INSERT INTO orders (
                user_id, order_number, status, payment_status, payment_method,
                subtotal, tax, shipping_fee, marketplace_fee, discount, total,
                shipping_full_name, shipping_phone, shipping_address_line1,
                shipping_address_line2, shipping_city, shipping_state,
                shipping_postal_code, shipping_country, delivery_option,
                estimated_delivery_date, customer_notes
            ) VALUES (
                %s, %s, 'pending', 'pending', %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        cursor.execute(order_query, (
            current_user["id"],
            order_number,
            checkout_data.payment_method.value,
            float(subtotal),
            float(tax),
            float(shipping_fee),
            float(marketplace_fee),
            float(discount),
            float(total),
            checkout_data.shipping_address.full_name,
            checkout_data.shipping_address.phone,
            checkout_data.shipping_address.address_line1,
            checkout_data.shipping_address.address_line2,
            checkout_data.shipping_address.city,
            checkout_data.shipping_address.state,
            checkout_data.shipping_address.postal_code,
            checkout_data.shipping_address.country,
            checkout_data.delivery_option.value,
            estimated_delivery.date(),
            checkout_data.customer_notes
        ))
        
        # Get the created order ID
        order_id = cursor.lastrowid
        
        # Create order items
        for item in items:
            order_item_query = """
                INSERT INTO order_items (
                    order_id, product_id, variant_id, product_name,
                    variant_name, variant_value, sku, quantity, price, subtotal
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            item_subtotal = Decimal(str(item['price_at_time'])) * item['quantity']
            cursor.execute(order_item_query, (
                order_id,
                item['product_id'],
                item['variant_id'],
                item['product_name'],
                item['variant_name'],
                item['variant_value'],
                item['variant_sku'] or item['sku'],
                item['quantity'],
                float(item['price_at_time']),
                float(item_subtotal)
            ))
        
        # Create order status history
        status_history_query = """
            INSERT INTO order_status_history (order_id, status, notes)
            VALUES (%s, 'pending', 'Order created')
        """
        cursor.execute(status_history_query, (order_id,))
        
        # Clear cart items
        cursor.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))
        
        connection.commit()
        
        # Format response
        order_items = [
            OrderItemResponse(
                product_id=item['product_id'],
                variant_id=item['variant_id'],
                quantity=item['quantity'],
                price=Decimal(str(item['price_at_time'])),
                subtotal=Decimal(str(item['price_at_time'])) * item['quantity'],
                product_name=item['product_name'],
                variant_name=item['variant_name'],
                variant_value=item['variant_value'],
                image_url=item['image_url']
            )
            for item in items
        ]
        
        return OrderResponse(
            order_id=order_id,
            order_number=order_number,
            status="pending",
            payment_status="pending",
            payment_method=checkout_data.payment_method.value,
            subtotal=subtotal,
            tax=tax,
            shipping_fee=shipping_fee,
            marketplace_fee=marketplace_fee,
            discount=discount,
            total=total,
            shipping_address=checkout_data.shipping_address,
            delivery_option=checkout_data.delivery_option.value,
            estimated_delivery_date=estimated_delivery.date(),
            customer_notes=checkout_data.customer_notes,
            items=order_items,
            created_at=datetime.now()
        )
        
    except HTTPException:
        if connection:
            connection.rollback()
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error in process_checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process checkout: {str(e)}"
        )
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()