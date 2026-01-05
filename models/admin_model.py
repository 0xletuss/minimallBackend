import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
from typing import Optional

class AdminModel:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('MYSQLHOST'),
                user=os.getenv('MYSQLUSER'),
                password=os.getenv('MYSQLPASSWORD'),
                database=os.getenv('MYSQLDATABASE'),
                port=int(os.getenv('MYSQLPORT', 3306))
            )
            self.cursor = self.connection.cursor(dictionary=True)
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
    
    def ensure_connection(self):
        try:
            if not self.connection.is_connected():
                self.connect()
        except:
            self.connect()
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        self.ensure_connection()
        
        stats = {}
        
        # Total users
        self.cursor.execute("SELECT COUNT(*) as total FROM users")
        stats['total_users'] = self.cursor.fetchone()['total']
        
        # Total orders
        self.cursor.execute("SELECT COUNT(*) as total FROM orders")
        stats['total_orders'] = self.cursor.fetchone()['total']
        
        # Total revenue
        self.cursor.execute("SELECT SUM(total) as revenue FROM orders WHERE payment_status = 'paid'")
        result = self.cursor.fetchone()
        stats['total_revenue'] = float(result['revenue']) if result['revenue'] else 0.0
        
        # Total products
        self.cursor.execute("SELECT COUNT(*) as total FROM products WHERE is_active = 1")
        stats['total_products'] = self.cursor.fetchone()['total']
        
        # Pending orders
        self.cursor.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'")
        stats['pending_orders'] = self.cursor.fetchone()['total']
        
        # Pending seller applications
        self.cursor.execute("SELECT COUNT(*) as total FROM seller_applications WHERE status = 'pending'")
        stats['pending_applications'] = self.cursor.fetchone()['total']
        
        # Active sellers
        self.cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_seller = 1 AND seller_status = 'active'")
        stats['active_sellers'] = self.cursor.fetchone()['total']
        
        # Today's orders
        self.cursor.execute("""
            SELECT COUNT(*) as total, SUM(total) as revenue 
            FROM orders 
            WHERE DATE(created_at) = CURDATE()
        """)
        today = self.cursor.fetchone()
        stats['today_orders'] = today['total']
        stats['today_revenue'] = float(today['revenue']) if today['revenue'] else 0.0
        
        # This month's stats
        self.cursor.execute("""
            SELECT COUNT(*) as total, SUM(total) as revenue 
            FROM orders 
            WHERE YEAR(created_at) = YEAR(CURDATE()) 
            AND MONTH(created_at) = MONTH(CURDATE())
        """)
        month = self.cursor.fetchone()
        stats['month_orders'] = month['total']
        stats['month_revenue'] = float(month['revenue']) if month['revenue'] else 0.0
        
        return stats
    
    def get_all_users(self, page: int, limit: int, search: Optional[str], role: Optional[str]):
        """Get all users with pagination"""
        self.ensure_connection()
        
        offset = (page - 1) * limit
        
        query = """
            SELECT u.*, us.total_spent, us.purchased_products, us.loyalty_points
            FROM users u
            LEFT JOIN user_statistics us ON u.id = us.user_id
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (u.email LIKE %s OR u.full_name LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])
        
        if role:
            query += " AND u.role = %s"
            params.append(role)
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
        self.cursor.execute(count_query, params)
        total = self.cursor.fetchone()['total']
        
        # Get paginated results
        query += " ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        self.cursor.execute(query, params)
        users = self.cursor.fetchall()
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    
    def update_user_status(self, user_id: int, is_active: bool):
        """Update user active status"""
        self.ensure_connection()
        
        self.cursor.execute(
            "UPDATE users SET is_active = %s WHERE id = %s",
            (is_active, user_id)
        )
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def get_seller_applications(self, status: Optional[str]):
        """Get seller applications"""
        self.ensure_connection()
        
        query = """
            SELECT sa.*, u.email, u.full_name, u.phone
            FROM seller_applications sa
            JOIN users u ON sa.user_id = u.id
        """
        
        if status:
            query += " WHERE sa.status = %s"
            self.cursor.execute(query + " ORDER BY sa.applied_at DESC", (status,))
        else:
            self.cursor.execute(query + " ORDER BY sa.applied_at DESC")
        
        return self.cursor.fetchall()
    
    def review_seller_application(self, application_id: int, status: str, 
                                  rejection_reason: Optional[str], reviewer_id: int):
        """Approve or reject seller application"""
        self.ensure_connection()
        
        # Get application details
        self.cursor.execute(
            "SELECT user_id, store_name, business_type FROM seller_applications WHERE id = %s",
            (application_id,)
        )
        application = self.cursor.fetchone()
        
        if not application:
            return False
        
        # Update application status
        self.cursor.execute("""
            UPDATE seller_applications 
            SET status = %s, rejection_reason = %s, reviewed_at = NOW(), reviewed_by = %s
            WHERE id = %s
        """, (status, rejection_reason, reviewer_id, application_id))
        
        if status == 'approved':
            # Update user to seller
            self.cursor.execute("""
                UPDATE users 
                SET is_seller = 1, seller_status = 'active', seller_activated_at = NOW()
                WHERE id = %s
            """, (application['user_id'],))
            
            # Create seller profile
            self.cursor.execute("""
                INSERT INTO seller_profiles 
                (user_id, store_name, business_type, seller_status)
                VALUES (%s, %s, %s, 'active')
            """, (application['user_id'], application['store_name'], application['business_type']))
        
        self.connection.commit()
        return True
    
    def get_all_orders(self, page: int, limit: int, status: Optional[str], search: Optional[str]):
        """Get all orders with pagination"""
        self.ensure_connection()
        
        offset = (page - 1) * limit
        
        query = """
            SELECT o.*, u.email, u.full_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND o.status = %s"
            params.append(status)
        
        if search:
            query += " AND (o.order_number LIKE %s OR u.email LIKE %s OR u.full_name LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
        self.cursor.execute(count_query, params)
        total = self.cursor.fetchone()['total']
        
        # Get paginated results
        query += " ORDER BY o.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        self.cursor.execute(query, params)
        orders = self.cursor.fetchall()
        
        return {
            'orders': orders,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    
    def get_order_details(self, order_id: int):
        """Get detailed order information"""
        self.ensure_connection()
        
        # Get order info
        self.cursor.execute("""
            SELECT o.*, u.email, u.full_name as customer_name, u.phone as customer_phone
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s
        """, (order_id,))
        order = self.cursor.fetchone()
        
        if not order:
            return None
        
        # Get order items
        self.cursor.execute("""
            SELECT oi.*, p.name as product_name, pi.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN product_images pi ON p.id = pi.product_id AND pi.is_primary = 1
            WHERE oi.order_id = %s
        """, (order_id,))
        order['items'] = self.cursor.fetchall()
        
        # Get status history
        self.cursor.execute("""
            SELECT * FROM order_status_history
            WHERE order_id = %s
            ORDER BY created_at DESC
        """, (order_id,))
        order['status_history'] = self.cursor.fetchall()
        
        return order
    
    def update_order_status(self, order_id: int, status: str, notes: Optional[str], admin_id: int):
        """Update order status"""
        self.ensure_connection()
        
        # Update order
        self.cursor.execute(
            "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, order_id)
        )
        
        # Add to status history
        self.cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes, created_by)
            VALUES (%s, %s, %s, %s)
        """, (order_id, status, notes, admin_id))
        
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def get_all_products(self, page: int, limit: int, search: Optional[str], category_id: Optional[int]):
        """Get all products with pagination"""
        self.ensure_connection()
        
        offset = (page - 1) * limit
        
        query = """
            SELECT p.*, c.name as category_name, u.full_name as seller_name,
                   pi.image_url
            FROM products p
            JOIN categories c ON p.category_id = c.id
            LEFT JOIN users u ON p.seller_id = u.id
            LEFT JOIN product_images pi ON p.id = pi.product_id AND pi.is_primary = 1
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND p.name LIKE %s"
            params.append(f"%{search}%")
        
        if category_id:
            query += " AND p.category_id = %s"
            params.append(category_id)
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
        self.cursor.execute(count_query, params)
        total = self.cursor.fetchone()['total']
        
        # Get paginated results
        query += " ORDER BY p.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        self.cursor.execute(query, params)
        products = self.cursor.fetchall()
        
        return {
            'products': products,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    
    def update_product_status(self, product_id: int, is_active: bool):
        """Update product active status"""
        self.ensure_connection()
        
        self.cursor.execute(
            "UPDATE products SET is_active = %s WHERE id = %s",
            (is_active, product_id)
        )
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def delete_product(self, product_id: int):
        """Delete a product"""
        self.ensure_connection()
        
        self.cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def get_revenue_analytics(self, period: str, start_date: Optional[str], end_date: Optional[str]):
        """Get revenue analytics"""
        self.ensure_connection()
        
        if period == 'daily':
            date_format = '%Y-%m-%d'
            group_by = 'DATE(created_at)'
        elif period == 'weekly':
            date_format = '%Y-W%u'
            group_by = 'YEARWEEK(created_at)'
        elif period == 'monthly':
            date_format = '%Y-%m'
            group_by = 'DATE_FORMAT(created_at, "%Y-%m")'
        else:  # yearly
            date_format = '%Y'
            group_by = 'YEAR(created_at)'
        
        query = f"""
            SELECT {group_by} as period,
                   COUNT(*) as order_count,
                   SUM(total) as revenue,
                   AVG(total) as avg_order_value
            FROM orders
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)
        
        query += f" GROUP BY {group_by} ORDER BY period DESC LIMIT 30"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_top_products(self, limit: int):
        """Get top selling products"""
        self.ensure_connection()
        
        self.cursor.execute("""
            SELECT p.id, p.name, p.price, pi.image_url,
                   COUNT(oi.id) as order_count,
                   SUM(oi.quantity) as total_sold,
                   SUM(oi.subtotal) as revenue
            FROM products p
            JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN product_images pi ON p.id = pi.product_id AND pi.is_primary = 1
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT %s
        """, (limit,))
        
        return self.cursor.fetchall()
    
    def get_top_sellers(self, limit: int):
        """Get top sellers by revenue"""
        self.ensure_connection()
        
        self.cursor.execute("""
            SELECT u.id, u.full_name, u.email,
                   sp.store_name,
                   COUNT(DISTINCT o.id) as order_count,
                   SUM(o.total) as revenue
            FROM users u
            JOIN seller_profiles sp ON u.id = sp.user_id
            JOIN products p ON u.id = p.seller_id
            JOIN order_items oi ON p.id = oi.product_id
            JOIN orders o ON oi.order_id = o.id
            WHERE u.is_seller = 1
            GROUP BY u.id
            ORDER BY revenue DESC
            LIMIT %s
        """, (limit,))
        
        return self.cursor.fetchall()
    
    def __del__(self):
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()