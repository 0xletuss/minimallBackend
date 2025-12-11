# checkout_model.py - Database Model for Checkout

import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any, List
import os
from datetime import datetime, timedelta

class CheckoutModel:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'railway'),
            'port': int(os.getenv('MYSQL_PORT', 3306))
        }
    
    def get_connection(self):
        """Get database connection"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    def create_order(
        self,
        user_id: int,
        payment_method: str,
        shipping_info: Dict[str, str],
        delivery_option: str = 'standard',
        customer_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create order from user's cart"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get cart items
            cart_query = """
                SELECT 
                    ci.cart_id,
                    ci.product_id,
                    ci.variant_id,
                    ci.quantity,
                    ci.price_at_time,
                    p.name as product_name,
                    pv.variant_name,
                    pv.variant_value,
                    p.sku,
                    p.quantity_in_stock as product_stock,
                    pv.quantity_in_stock as variant_stock
                FROM cart_items ci
                JOIN cart c ON ci.cart_id = c.cart_id
                JOIN products p ON ci.product_id = p.id
                LEFT JOIN product_variants pv ON ci.variant_id = pv.id
                WHERE c.user_id = %s
            """
            cursor.execute(cart_query, (user_id,))
            cart_items = cursor.fetchall()
            
            if not cart_items:
                return {'success': False, 'message': 'Cart is empty'}
            
            # Check stock availability
            for item in cart_items:
                available_stock = item['variant_stock'] if item['variant_id'] else item['product_stock']
                if available_stock < item['quantity']:
                    product_name = item['product_name']
                    return {
                        'success': False, 
                        'message': f'Insufficient stock for {product_name}. Available: {available_stock}, Requested: {item["quantity"]}'
                    }
            
            # Calculate totals
            subtotal = sum(float(item['price_at_time']) * item['quantity'] for item in cart_items)
            tax = subtotal * 0.12  # 12% tax
            
            # Calculate shipping fee based on delivery option
            shipping_fees = {
                'standard': 50.00,
                'express': 150.00,
                'same_day': 300.00,
                'pickup': 0.00
            }
            shipping_fee = shipping_fees.get(delivery_option, 50.00)
            
            marketplace_fee = subtotal * 0.02  # 2% marketplace fee
            total = subtotal + tax + shipping_fee + marketplace_fee
            
            # Call stored procedure to create order
            args = [
                user_id,
                payment_method,
                subtotal,
                tax,
                shipping_fee,
                marketplace_fee,
                total,
                shipping_info['full_name'],
                shipping_info['phone'],
                shipping_info['address_line1'],
                shipping_info.get('address_line2', ''),
                shipping_info['city'],
                shipping_info['state'],
                shipping_info['postal_code'],
                delivery_option,
                customer_notes
            ]
            
            result = cursor.callproc('create_order', args + [0, ''])
            
            # Fetch the OUT parameters
            cursor.execute("SELECT @_create_order_16 AS order_id, @_create_order_17 AS order_number")
            proc_result = cursor.fetchone()
            order_id = proc_result['order_id']
            order_number = proc_result['order_number']
            
            if not order_id:
                connection.rollback()
                return {'success': False, 'message': 'Failed to create order'}
            
            # Insert order items
            for item in cart_items:
                item_subtotal = float(item['price_at_time']) * item['quantity']
                insert_item_query = """
                    INSERT INTO order_items (
                        order_id, product_id, variant_id, product_name,
                        variant_name, variant_value, sku, quantity, price, subtotal
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_item_query, (
                    order_id,
                    item['product_id'],
                    item['variant_id'],
                    item['product_name'],
                    item['variant_name'],
                    item['variant_value'],
                    item['sku'],
                    item['quantity'],
                    item['price_at_time'],
                    item_subtotal
                ))
                
                # Update stock quantities
                if item['variant_id']:
                    cursor.execute(
                        "UPDATE product_variants SET quantity_in_stock = quantity_in_stock - %s WHERE id = %s",
                        (item['quantity'], item['variant_id'])
                    )
                else:
                    cursor.execute(
                        "UPDATE products SET quantity_in_stock = quantity_in_stock - %s WHERE id = %s",
                        (item['quantity'], item['product_id'])
                    )
            
            # Clear the cart
            cursor.execute(
                "DELETE FROM cart_items WHERE cart_id = (SELECT cart_id FROM cart WHERE user_id = %s)",
                (user_id,)
            )
            
            # Create initial payment transaction
            cursor.execute("""
                INSERT INTO payment_transactions (order_id, payment_method, amount, status)
                VALUES (%s, %s, %s, 'pending')
            """, (order_id, payment_method, total))
            
            connection.commit()
            
            return {
                'success': True,
                'message': 'Order created successfully',
                'order_id': order_id,
                'order_number': order_number,
                'total': float(total),
                'subtotal': float(subtotal),
                'tax': float(tax),
                'shipping_fee': float(shipping_fee),
                'marketplace_fee': float(marketplace_fee)
            }
            
        except Error as e:
            print(f"Error creating order: {e}")
            if connection:
                connection.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_order(self, order_id: int, user_id: int) -> Dict[str, Any]:
        """Get order details"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get order details
            order_query = """
                SELECT * FROM orders 
                WHERE id = %s AND user_id = %s
            """
            cursor.execute(order_query, (order_id, user_id))
            order = cursor.fetchone()
            
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            # Get order items
            items_query = """
                SELECT * FROM order_items 
                WHERE order_id = %s
            """
            cursor.execute(items_query, (order_id,))
            items = cursor.fetchall()
            
            # Convert decimals to float
            for key in ['subtotal', 'tax', 'shipping_fee', 'marketplace_fee', 'discount', 'total']:
                if order.get(key):
                    order[key] = float(order[key])
            
            for item in items:
                item['price'] = float(item['price'])
                item['subtotal'] = float(item['subtotal'])
            
            order['items'] = items
            
            return {
                'success': True,
                'order': order
            }
            
        except Error as e:
            print(f"Error getting order: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_user_orders(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get user's order history"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    o.*,
                    COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = %s
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            orders = cursor.fetchall()
            
            # Convert decimals to float
            for order in orders:
                for key in ['subtotal', 'tax', 'shipping_fee', 'marketplace_fee', 'discount', 'total']:
                    if order.get(key):
                        order[key] = float(order[key])
            
            return {
                'success': True,
                'orders': orders
            }
            
        except Error as e:
            print(f"Error getting orders: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_order_status(
        self,
        order_id: int,
        status: str,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update order status"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Update order status
            update_query = "UPDATE orders SET status = %s WHERE id = %s"
            cursor.execute(update_query, (status, order_id))
            
            # Add status history
            history_query = """
                INSERT INTO order_status_history (order_id, status, notes, created_by)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(history_query, (order_id, status, notes, user_id))
            
            # Update timestamp based on status
            if status == 'shipped':
                cursor.execute("UPDATE orders SET shipped_at = NOW() WHERE id = %s", (order_id,))
            elif status == 'delivered':
                cursor.execute("UPDATE orders SET delivered_at = NOW() WHERE id = %s", (order_id,))
            elif status == 'cancelled':
                cursor.execute("UPDATE orders SET cancelled_at = NOW() WHERE id = %s", (order_id,))
            
            connection.commit()
            
            return {
                'success': True,
                'message': 'Order status updated'
            }
            
        except Error as e:
            print(f"Error updating order status: {e}")
            if connection:
                connection.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_payment_status(
        self,
        order_id: int,
        payment_status: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update payment status"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Update order payment status
            cursor.execute(
                "UPDATE orders SET payment_status = %s WHERE id = %s",
                (payment_status, order_id)
            )
            
            if payment_status == 'paid':
                cursor.execute("UPDATE orders SET paid_at = NOW() WHERE id = %s", (order_id,))
            
            # Update payment transaction
            if transaction_id:
                cursor.execute("""
                    UPDATE payment_transactions 
                    SET status = %s, transaction_id = %s, updated_at = NOW()
                    WHERE order_id = %s
                """, (payment_status, transaction_id, order_id))
            else:
                cursor.execute("""
                    UPDATE payment_transactions 
                    SET status = %s, updated_at = NOW()
                    WHERE order_id = %s
                """, (payment_status, order_id))
            
            connection.commit()
            
            return {
                'success': True,
                'message': 'Payment status updated'
            }
            
        except Error as e:
            print(f"Error updating payment status: {e}")
            if connection:
                connection.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()