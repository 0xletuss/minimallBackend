import mysql.connector
from datetime import datetime, timedelta
from decimal import Decimal
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

load_dotenv()

class OrderModel:
    
    def __init__(self):
        self.db_config = {
           'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'railway'),
            'port': int(os.getenv('MYSQL_PORT', 3306))
        }
    
    def get_connection(self):
        return mysql.connector.connect(**self.db_config)
    
    def _convert_decimals(self, data: Any) -> Any:
        """Recursively convert Decimal objects to float for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._convert_decimals(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_decimals(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        return data
    
    # ==================== USER & SELLER VERIFICATION ====================
    
    def get_user_seller_info(self, user_id: int) -> Optional[Dict]:
        """Get user seller information from seller_profiles table"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT 
                    u.id,
                    u.email,
                    u.is_seller,
                    u.role,
                    sp.seller_status,
                    sp.store_name,
                    sp.commission_rate
                FROM users u
                LEFT JOIN seller_profiles sp ON u.id = sp.user_id
                WHERE u.id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    def get_user_seller_status(self, user_id: int) -> Optional[Dict]:
        """Check if user is an active seller"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT id, is_seller, seller_status, role
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    
    def seller_has_items_in_order(self, order_id: int, seller_id: int) -> bool:
        """Check if seller has products in this order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s AND p.seller_id = %s
            """, (order_id, seller_id))
            
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        finally:
            cursor.close()
            conn.close()
    
    # ==================== SELLER ORDER QUERIES ====================
    
    def get_seller_orders(
        self, 
        seller_id: int, 
        page: int = 1, 
        limit: int = 10, 
        status: Optional[str] = None, 
        date_from: Optional[datetime] = None, 
        search_term: Optional[str] = None
    ) -> List[Dict]:
        """Get all orders containing seller's products"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            offset = (page - 1) * limit
            
            # Build WHERE clause
            where_conditions = ["p.seller_id = %s"]
            params = [seller_id]
            
            if status:
                where_conditions.append("o.status = %s")
                params.append(status)
            
            if date_from:
                where_conditions.append("o.created_at >= %s")
                params.append(date_from)
            
            if search_term:
                where_conditions.append("""
                    (o.order_number LIKE %s OR 
                     o.shipping_full_name LIKE %s OR
                     u.email LIKE %s)
                """)
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            where_clause = " AND ".join(where_conditions)
            
            # Main query - get orders with seller's products
            query = f"""
                SELECT DISTINCT
                    o.id,
                    o.order_number,
                    o.user_id,
                    o.status,
                    o.payment_status,
                    o.payment_method,
                    o.delivery_option,
                    o.created_at,
                    o.shipping_full_name as customer_name,
                    u.email as customer_email,
                    COUNT(DISTINCT oi.id) as item_count,
                    SUM(oi.subtotal) as seller_subtotal,
                    COALESCE(sp.commission_rate, 10.00) as commission_rate,
                    (SUM(oi.subtotal) * COALESCE(sp.commission_rate, 10.00) / 100) as marketplace_fee,
                    (SUM(oi.subtotal) - (SUM(oi.subtotal) * COALESCE(sp.commission_rate, 10.00) / 100)) as seller_payout
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                LEFT JOIN seller_profiles sp ON p.seller_id = sp.user_id
                WHERE {where_clause}
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            cursor.execute(query, params)
            
            orders = cursor.fetchall()
            return self._convert_decimals(orders)
        finally:
            cursor.close()
            conn.close()
    
    def count_seller_orders(
        self, 
        seller_id: int, 
        status: Optional[str] = None, 
        date_from: Optional[datetime] = None, 
        search_term: Optional[str] = None
    ) -> int:
        """Count total orders for seller"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            where_conditions = ["p.seller_id = %s"]
            params = [seller_id]
            
            if status:
                where_conditions.append("o.status = %s")
                params.append(status)
            
            if date_from:
                where_conditions.append("o.created_at >= %s")
                params.append(date_from)
            
            if search_term:
                where_conditions.append("""
                    (o.order_number LIKE %s OR 
                     o.shipping_full_name LIKE %s OR
                     u.email LIKE %s)
                """)
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT COUNT(DISTINCT o.id) as total
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE {where_clause}
            """
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return result[0] if result else 0
        finally:
            cursor.close()
            conn.close()
    
    def get_seller_order_details(self, order_id: int, seller_id: int) -> Optional[Dict]:
        """Get detailed order information with only seller's items"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get order information
            cursor.execute("""
                SELECT DISTINCT
                    o.*,
                    u.email as customer_email,
                    sp.store_name,
                    COALESCE(sp.commission_rate, 10.00) as commission_rate
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                LEFT JOIN seller_profiles sp ON p.seller_id = sp.user_id
                WHERE o.id = %s AND p.seller_id = %s
            """, (order_id, seller_id))
            
            order = cursor.fetchone()
            
            if not order:
                return None
            
            # Get seller's items in this order
            cursor.execute("""
                SELECT 
                    oi.*,
                    p.name as product_name,
                    p.seller_id
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s AND p.seller_id = %s
            """, (order_id, seller_id))
            
            items = cursor.fetchall()
            
            # Calculate seller-specific totals
            seller_subtotal = sum(float(item['subtotal']) for item in items)
            commission_rate = float(order['commission_rate']) if order['commission_rate'] else 10.0
            marketplace_fee = seller_subtotal * (commission_rate / 100)
            seller_payout = seller_subtotal - marketplace_fee
            
            # Add calculated fields
            order['items'] = items
            order['item_count'] = len(items)
            order['seller_subtotal'] = seller_subtotal
            order['marketplace_fee'] = marketplace_fee
            order['seller_payout'] = seller_payout
            
            return self._convert_decimals(order)
        finally:
            cursor.close()
            conn.close()
    
    def get_seller_order_stats(self, seller_id: int) -> Dict:
        """Get order statistics for seller"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get counts by status
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT CASE WHEN o.status = 'pending' THEN o.id END) as pending_count,
                    COUNT(DISTINCT CASE WHEN o.status = 'processing' THEN o.id END) as processing_count,
                    COUNT(DISTINCT CASE WHEN o.status = 'shipped' THEN o.id END) as shipped_count,
                    COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN o.id END) as delivered_count,
                    COUNT(DISTINCT CASE WHEN o.status = 'cancelled' THEN o.id END) as cancelled_count,
                    COUNT(DISTINCT o.id) as total_orders,
                    SUM(oi.subtotal) as total_revenue,
                    AVG(oi.subtotal) as avg_order_value
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id = %s
            """, (seller_id,))
            
            stats = cursor.fetchone()
            return self._convert_decimals(stats)
        finally:
            cursor.close()
            conn.close()
    
    def get_seller_revenue_data(self, seller_id: int, days: int = 30) -> List[Dict]:
        """Get revenue data for charts"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT 
                    DATE(o.created_at) as order_date,
                    SUM(oi.subtotal) as revenue,
                    COUNT(DISTINCT o.id) as order_count
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE p.seller_id = %s 
                AND o.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                AND o.status NOT IN ('cancelled', 'refunded')
                GROUP BY DATE(o.created_at)
                ORDER BY order_date ASC
            """, (seller_id, days))
            
            data = cursor.fetchall()
            return self._convert_decimals(data)
        finally:
            cursor.close()
            conn.close()
    
    # ==================== ORDER STATUS MANAGEMENT ====================
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get basic order information"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()
            return self._convert_decimals(order) if order else None
        finally:
            cursor.close()
            conn.close()
    
    def update_order_status(
        self, 
        order_id: int, 
        status: str, 
        tracking_number: Optional[str] = None
    ) -> bool:
        """Update order status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            update_fields = ["status = %s"]
            params = [status]
            
            # Set timestamp fields based on status
            if status == 'shipped':
                update_fields.append("shipped_at = NOW()")
                if tracking_number:
                    update_fields.append("tracking_number = %s")
                    params.append(tracking_number)
            elif status == 'delivered':
                update_fields.append("delivered_at = NOW()")
            elif status == 'cancelled':
                update_fields.append("cancelled_at = NOW()")
            
            params.append(order_id)
            
            query = f"""
                UPDATE orders 
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = %s
            """
            
            cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    
    def add_status_history(
        self, 
        order_id: int, 
        status: str, 
        notes: Optional[str] = None, 
        created_by: Optional[int] = None
    ) -> bool:
        """Add entry to order status history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO order_status_history 
                (order_id, status, notes, created_by)
                VALUES (%s, %s, %s, %s)
            """, (order_id, status, notes, created_by))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    
    def get_order_status_history(self, order_id: int) -> List[Dict]:
        """Get order status history"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM order_status_history
                WHERE order_id = %s
                ORDER BY created_at DESC
            """, (order_id,))
            
            history = cursor.fetchall()
            return self._convert_decimals(history)
        finally:
            cursor.close()
            conn.close()
    
    def restore_inventory_for_order(self, order_id: int, seller_id: int) -> bool:
        """Restore inventory when order is cancelled"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Restore product quantities
            cursor.execute("""
                UPDATE products p
                JOIN order_items oi ON p.id = oi.product_id
                SET p.quantity_in_stock = p.quantity_in_stock + oi.quantity
                WHERE oi.order_id = %s AND p.seller_id = %s
            """, (order_id, seller_id))
            
            # Restore variant quantities if applicable
            cursor.execute("""
                UPDATE product_variants pv
                JOIN order_items oi ON pv.id = oi.variant_id
                JOIN products p ON pv.product_id = p.id
                SET pv.quantity_in_stock = pv.quantity_in_stock + oi.quantity
                WHERE oi.order_id = %s AND p.seller_id = %s AND oi.variant_id IS NOT NULL
            """, (order_id, seller_id))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    
    # ==================== CUSTOMER ORDER QUERIES ====================
    
    def get_customer_orders(
        self, 
        user_id: int, 
        page: int = 1, 
        limit: int = 10, 
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get customer's orders"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            offset = (page - 1) * limit
            
            where_clause = "o.user_id = %s"
            params = [user_id]
            
            if status:
                where_clause += " AND o.status = %s"
                params.append(status)
            
            query = f"""
                SELECT 
                    o.*,
                    COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE {where_clause}
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            cursor.execute(query, params)
            
            orders = cursor.fetchall()
            return self._convert_decimals(orders)
        finally:
            cursor.close()
            conn.close()
    
    def count_customer_orders(self, user_id: int, status: Optional[str] = None) -> int:
        """Count customer orders"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            where_clause = "user_id = %s"
            params = [user_id]
            
            if status:
                where_clause += " AND status = %s"
                params.append(status)
            
            cursor.execute(f"SELECT COUNT(*) FROM orders WHERE {where_clause}", params)
            result = cursor.fetchone()
            
            return result[0] if result else 0
        finally:
            cursor.close()
            conn.close()
    
    def get_customer_order_details(self, order_id: int, user_id: int) -> Optional[Dict]:
        """Get customer order details"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM orders 
                WHERE id = %s AND user_id = %s
            """, (order_id, user_id))
            
            order = cursor.fetchone()
            
            if not order:
                return None
            
            # Get all order items
            cursor.execute("""
                SELECT oi.*, p.name as product_name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            items = cursor.fetchall()
            order['items'] = items
            
            return self._convert_decimals(order)
        finally:
            cursor.close()
            conn.close()