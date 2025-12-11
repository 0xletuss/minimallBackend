import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any, List
import os

class CartModel:
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
    
    def get_or_create_cart(self, user_id: int) -> Optional[int]:
        """Get existing cart or create new one for user"""
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if cart exists
            cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
            cart = cursor.fetchone()
            
            if cart:
                return cart['cart_id']
            
            # Create new cart
            cursor.execute("INSERT INTO cart (user_id) VALUES (%s)", (user_id,))
            connection.commit()
            return cursor.lastrowid
            
        except Error as e:
            print(f"Error getting/creating cart: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def add_item(
        self, 
        user_id: int, 
        product_id: int, 
        quantity: int = 1,
        variant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add item to cart"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get or create cart
            cart_id = self.get_or_create_cart(user_id)
            if not cart_id:
                return {'success': False, 'message': 'Failed to create cart'}
            
            # Get product price
            if variant_id:
                cursor.execute(
                    "SELECT price FROM product_variants WHERE id = %s", 
                    (variant_id,)
                )
            else:
                cursor.execute(
                    "SELECT price FROM products WHERE id = %s", 
                    (product_id,)
                )
            
            product = cursor.fetchone()
            if not product:
                return {'success': False, 'message': 'Product not found'}
            
            price = product['price']
            
            # Check if item already exists in cart
            check_query = """
                SELECT cart_item_id, quantity 
                FROM cart_items 
                WHERE cart_id = %s AND product_id = %s 
                AND (variant_id = %s OR (variant_id IS NULL AND %s IS NULL))
            """
            cursor.execute(check_query, (cart_id, product_id, variant_id, variant_id))
            existing_item = cursor.fetchone()
            
            if existing_item:
                # Update quantity
                new_quantity = existing_item['quantity'] + quantity
                update_query = """
                    UPDATE cart_items 
                    SET quantity = %s, price_at_time = %s 
                    WHERE cart_item_id = %s
                """
                cursor.execute(update_query, (new_quantity, price, existing_item['cart_item_id']))
            else:
                # Insert new item
                insert_query = """
                    INSERT INTO cart_items (cart_id, product_id, variant_id, quantity, price_at_time)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (cart_id, product_id, variant_id, quantity, price))
            
            connection.commit()
            
            return {
                'success': True,
                'message': 'Item added to cart',
                'cart_id': cart_id
            }
            
        except Error as e:
            print(f"Error adding item to cart: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_cart(self, user_id: int) -> Dict[str, Any]:
        """Get user's cart with all items"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get cart
            cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
            cart = cursor.fetchone()
            
            if not cart:
                return {
                    'success': True,
                    'cart': {
                        'items': [],
                        'total': 0,
                        'item_count': 0
                    }
                }
            
            cart_id = cart['cart_id']
            
            # Get cart items with product details
            query = """
                SELECT 
                    ci.cart_item_id,
                    ci.product_id,
                    ci.variant_id,
                    ci.quantity,
                    ci.price_at_time,
                    ci.added_at,
                    p.name as product_name,
                    p.slug as product_slug,
                    p.image_url as product_image,
                    p.stock as product_stock,
                    pv.name as variant_name,
                    pv.stock as variant_stock,
                    COALESCE(pv.price, p.price) as current_price
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                LEFT JOIN product_variants pv ON ci.variant_id = pv.id
                WHERE ci.cart_id = %s
                ORDER BY ci.added_at DESC
            """
            cursor.execute(query, (cart_id,))
            items = cursor.fetchall()
            
            # Calculate totals
            total = sum(item['price_at_time'] * item['quantity'] for item in items)
            item_count = sum(item['quantity'] for item in items)
            
            return {
                'success': True,
                'cart': {
                    'cart_id': cart_id,
                    'items': items,
                    'total': float(total),
                    'item_count': item_count
                }
            }
            
        except Error as e:
            print(f"Error getting cart: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_item_quantity(
        self, 
        user_id: int, 
        cart_item_id: int, 
        quantity: int
    ) -> Dict[str, Any]:
        """Update quantity of cart item"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Verify item belongs to user's cart
            verify_query = """
                SELECT ci.cart_item_id 
                FROM cart_items ci
                JOIN cart c ON ci.cart_id = c.cart_id
                WHERE ci.cart_item_id = %s AND c.user_id = %s
            """
            cursor.execute(verify_query, (cart_item_id, user_id))
            
            if not cursor.fetchone():
                return {'success': False, 'message': 'Cart item not found'}
            
            if quantity <= 0:
                return {'success': False, 'message': 'Quantity must be greater than 0'}
            
            # Update quantity
            update_query = """
                UPDATE cart_items 
                SET quantity = %s 
                WHERE cart_item_id = %s
            """
            cursor.execute(update_query, (quantity, cart_item_id))
            connection.commit()
            
            return {
                'success': True,
                'message': 'Cart item updated'
            }
            
        except Error as e:
            print(f"Error updating cart item: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def remove_item(self, user_id: int, cart_item_id: int) -> Dict[str, Any]:
        """Remove item from cart"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Verify and delete item
            delete_query = """
                DELETE ci FROM cart_items ci
                JOIN cart c ON ci.cart_id = c.cart_id
                WHERE ci.cart_item_id = %s AND c.user_id = %s
            """
            cursor.execute(delete_query, (cart_item_id, user_id))
            connection.commit()
            
            if cursor.rowcount == 0:
                return {'success': False, 'message': 'Cart item not found'}
            
            return {
                'success': True,
                'message': 'Item removed from cart'
            }
            
        except Error as e:
            print(f"Error removing cart item: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def clear_cart(self, user_id: int) -> Dict[str, Any]:
        """Clear all items from user's cart"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get cart_id
            cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user_id,))
            cart = cursor.fetchone()
            
            if not cart:
                return {'success': True, 'message': 'Cart is already empty'}
            
            # Delete all items
            cursor.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart['cart_id'],))
            connection.commit()
            
            return {
                'success': True,
                'message': 'Cart cleared'
            }
            
        except Error as e:
            print(f"Error clearing cart: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_cart_count(self, user_id: int) -> int:
        """Get total number of items in cart"""
        connection = self.get_connection()
        if not connection:
            return 0
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT COALESCE(SUM(ci.quantity), 0) as count
                FROM cart c
                LEFT JOIN cart_items ci ON c.cart_id = ci.cart_id
                WHERE c.user_id = %s
            """
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            
            return int(result['count']) if result else 0
            
        except Error as e:
            print(f"Error getting cart count: {e}")
            return 0
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()