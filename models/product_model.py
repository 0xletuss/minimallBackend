import mysql.connector
from mysql.connector import Error
import os
from typing import Optional, Dict, Any, List

class ProductModel:
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
    
    def get_all_products(
        self, 
        limit: int = 50, 
        offset: int = 0,
        category_id: Optional[int] = None,
        is_featured: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all products with optional filters"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Build query with filters
            query = """
                SELECT p.*, c.name as category_name, c.slug as category_slug,
                       (SELECT image_url FROM product_images WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
            """
            params = []
            
            if category_id:
                query += " AND p.category_id = %s"
                params.append(category_id)
            
            if is_featured is not None:
                query += " AND p.is_featured = %s"
                params.append(1 if is_featured else 0)
            
            if search:
                query += " AND (p.name LIKE %s OR p.description LIKE %s)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term])
            
            query += " ORDER BY p.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            products = cursor.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM products WHERE is_active = 1"
            count_params = []
            
            if category_id:
                count_query += " AND category_id = %s"
                count_params.append(category_id)
            
            if is_featured is not None:
                count_query += " AND is_featured = %s"
                count_params.append(1 if is_featured else 0)
            
            if search:
                count_query += " AND (name LIKE %s OR description LIKE %s)"
                search_term = f"%{search}%"
                count_params.extend([search_term, search_term])
            
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            return {
                'success': True,
                'products': products,
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
        except Error as e:
            print(f"Error getting products: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_product_by_id(self, product_id: int) -> Dict[str, Any]:
        """Get single product by ID with images and variants"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get product details
            query = """
                SELECT p.*, c.name as category_name, c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s AND p.is_active = 1
            """
            cursor.execute(query, (product_id,))
            product = cursor.fetchone()
            
            if not product:
                return {'success': False, 'message': 'Product not found'}
            
            # Get product images
            cursor.execute(
                "SELECT * FROM product_images WHERE product_id = %s ORDER BY display_order",
                (product_id,)
            )
            product['images'] = cursor.fetchall()
            
            # Get product variants
            cursor.execute(
                "SELECT * FROM product_variants WHERE product_id = %s AND is_active = 1",
                (product_id,)
            )
            product['variants'] = cursor.fetchall()
            
            # Get product tags
            cursor.execute(
                "SELECT tag_name FROM product_tags WHERE product_id = %s",
                (product_id,)
            )
            product['tags'] = [row['tag_name'] for row in cursor.fetchall()]
            
            # Update view count
            cursor.execute(
                "UPDATE products SET view_count = view_count + 1 WHERE id = %s",
                (product_id,)
            )
            connection.commit()
            
            return {
                'success': True,
                'product': product
            }
            
        except Error as e:
            print(f"Error getting product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_product_by_slug(self, slug: str) -> Dict[str, Any]:
        """Get single product by slug"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get product ID from slug
            cursor.execute("SELECT id FROM products WHERE slug = %s AND is_active = 1", (slug,))
            result = cursor.fetchone()
            
            if not result:
                return {'success': False, 'message': 'Product not found'}
            
            # Use get_product_by_id to get full details
            return self.get_product_by_id(result['id'])
            
        except Error as e:
            print(f"Error getting product by slug: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_all_categories(self) -> Dict[str, Any]:
        """Get all active categories"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT c.*, 
                       COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
                WHERE c.is_active = 1
                GROUP BY c.id
                ORDER BY c.display_order, c.name
            """
            cursor.execute(query)
            categories = cursor.fetchall()
            
            return {
                'success': True,
                'categories': categories
            }
            
        except Error as e:
            print(f"Error getting categories: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_category_by_slug(self, slug: str) -> Dict[str, Any]:
        """Get category by slug"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT c.*, 
                       COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
                WHERE c.slug = %s AND c.is_active = 1
                GROUP BY c.id
            """
            cursor.execute(query, (slug,))
            category = cursor.fetchone()
            
            if not category:
                return {'success': False, 'message': 'Category not found'}
            
            return {
                'success': True,
                'category': category
            }
            
        except Error as e:
            print(f"Error getting category: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_featured_products(self, limit: int = 8) -> Dict[str, Any]:
        """Get featured products"""
        return self.get_all_products(limit=limit, is_featured=True)
    
    def search_products(self, search_term: str, limit: int = 20) -> Dict[str, Any]:
        """Search products by name or description"""
        return self.get_all_products(limit=limit, search=search_term)
    
    def get_products_by_tag(self, tag_name: str, limit: int = 20) -> Dict[str, Any]:
        """Get products by tag"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT p.*, c.name as category_name, c.slug as category_slug,
                       (SELECT image_url FROM product_images WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                INNER JOIN product_tags pt ON p.id = pt.product_id
                WHERE p.is_active = 1 AND pt.tag_name = %s
                ORDER BY p.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (tag_name, limit))
            products = cursor.fetchall()
            
            return {
                'success': True,
                'products': products,
                'tag': tag_name
            }
            
        except Error as e:
            print(f"Error getting products by tag: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()