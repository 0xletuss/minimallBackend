import mysql.connector
from mysql.connector import Error
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


class SellerProductModel:
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
    
    # ==================== SELLER VERIFICATION ====================
    
    def verify_seller(self, user_id: int) -> bool:
        """Check if user is an active seller"""
        connection = self.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT is_seller, seller_status 
                FROM users 
                WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            if not user:
                return False
            
            return user['is_seller'] and user['seller_status'] == 'active'
            
        except Error as e:
            print(f"Error verifying seller: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def verify_product_ownership(self, user_id: int, product_id: int) -> bool:
        """Check if product belongs to seller"""
        connection = self.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT seller_id 
                FROM products 
                WHERE id = %s
            """, (product_id,))
            
            product = cursor.fetchone()
            
            if not product:
                return False
            
            return product['seller_id'] == user_id
            
        except Error as e:
            print(f"Error verifying ownership: {e}")
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== GET SELLER PRODUCTS ====================
    
    def get_seller_products(
        self, 
        seller_id: int, 
        limit: int = 10, 
        offset: int = 0,
        status_filter: str = "all",
        search: str = ""
    ) -> Dict[str, Any]:
        """Get all products for a seller with filters"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Build WHERE clause based on filters
            where_conditions = ["p.seller_id = %s"]
            params = [seller_id]
            
            # Status filter
            if status_filter == "active":
                where_conditions.append("p.is_active = TRUE AND p.quantity_in_stock > 0")
            elif status_filter == "draft":
                where_conditions.append("p.is_active = FALSE")
            elif status_filter == "out_of_stock":
                where_conditions.append("p.is_active = TRUE AND p.quantity_in_stock = 0")
            
            # Search filter
            if search:
                where_conditions.append("(p.name LIKE %s OR p.sku LIKE %s OR p.description LIKE %s)")
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM products p
                WHERE {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # Get products with pagination
            query = f"""
                SELECT 
                    p.id,
                    p.name,
                    p.slug,
                    p.description,
                    p.short_description,
                    p.price,
                    p.compare_at_price,
                    p.sku,
                    p.quantity_in_stock,
                    p.weight,
                    p.is_featured,
                    p.is_active,
                    p.rating_average,
                    p.rating_count,
                    p.view_count,
                    p.created_at,
                    p.updated_at,
                    c.id as category_id,
                    c.name as category_name,
                    c.slug as category_slug,
                    (SELECT pi.image_url 
                     FROM product_images pi 
                     WHERE pi.product_id = p.id AND pi.is_primary = TRUE 
                     LIMIT 1) as primary_image
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE {where_clause}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            cursor.execute(query, params)
            products = cursor.fetchall() or []
            
            # Get status counts for tabs
            cursor.execute("""
                SELECT 
                    COUNT(*) as all_count,
                    SUM(CASE WHEN is_active = TRUE AND quantity_in_stock > 0 THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as draft_count,
                    SUM(CASE WHEN is_active = TRUE AND quantity_in_stock = 0 THEN 1 ELSE 0 END) as out_of_stock_count
                FROM products
                WHERE seller_id = %s
            """, (seller_id,))
            
            counts = cursor.fetchone()
            
            return {
                'success': True,
                'products': products,
                'total': total,
                'limit': limit,
                'offset': offset,
                'counts': {
                    'all': counts['all_count'] or 0,
                    'active': counts['active_count'] or 0,
                    'draft': counts['draft_count'] or 0,
                    'out_of_stock': counts['out_of_stock_count'] or 0
                }
            }
            
        except Error as e:
            print(f"Error getting seller products: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== GET SINGLE PRODUCT ====================
    
    def get_seller_product(self, seller_id: int, product_id: int) -> Dict[str, Any]:
        """Get single product details (must be owned by seller)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        # Verify ownership
        if not self.verify_product_ownership(seller_id, product_id):
            return {'success': False, 'message': 'Product not found or access denied'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get product details
            cursor.execute("""
                SELECT 
                    p.*,
                    c.name as category_name,
                    c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s AND p.seller_id = %s
            """, (product_id, seller_id))
            
            product = cursor.fetchone()
            
            if not product:
                return {'success': False, 'message': 'Product not found'}
            
            # Get product images
            cursor.execute("""
                SELECT id, image_url, alt_text, is_primary, display_order
                FROM product_images
                WHERE product_id = %s
                ORDER BY is_primary DESC, display_order ASC
            """, (product_id,))
            product['images'] = cursor.fetchall() or []
            
            # Get product variants
            cursor.execute("""
                SELECT id, variant_name, variant_value, price_modifier, 
                       sku, quantity_in_stock, is_active
                FROM product_variants
                WHERE product_id = %s
                ORDER BY variant_name, variant_value
            """, (product_id,))
            product['variants'] = cursor.fetchall() or []
            
            # Get product tags
            cursor.execute("""
                SELECT tag_name
                FROM product_tags
                WHERE product_id = %s
                ORDER BY tag_name
            """, (product_id,))
            product['tags'] = [row['tag_name'] for row in cursor.fetchall()]
            
            return {'success': True, 'product': product}
            
        except Error as e:
            print(f"Error getting product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== CREATE PRODUCT ====================
    
    def create_product(self, seller_id: int, product_data: dict) -> Dict[str, Any]:
        """Create new product"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if slug already exists
            cursor.execute("SELECT id FROM products WHERE slug = %s", (product_data['slug'],))
            if cursor.fetchone():
                return {'success': False, 'message': 'Product slug already exists'}
            
            # Check if SKU already exists (if provided)
            if product_data.get('sku'):
                cursor.execute("SELECT id FROM products WHERE sku = %s", (product_data['sku'],))
                if cursor.fetchone():
                    return {'success': False, 'message': 'SKU already exists'}
            
            # Insert product
            insert_query = """
                INSERT INTO products (
                    seller_id, category_id, name, slug, description, short_description,
                    price, compare_at_price, sku, quantity_in_stock, weight,
                    is_featured, is_active, requires_shipping, is_taxable,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """
            
            cursor.execute(insert_query, (
                seller_id,
                product_data['category_id'],
                product_data['name'],
                product_data['slug'],
                product_data.get('description'),
                product_data.get('short_description'),
                product_data['price'],
                product_data.get('compare_at_price'),
                product_data.get('sku'),
                product_data['quantity_in_stock'],
                product_data.get('weight'),
                product_data.get('is_featured', False),
                product_data.get('is_active', True),
                True,  # requires_shipping
                True   # is_taxable
            ))
            
            product_id = cursor.lastrowid
            
            # Add product image if provided
            if product_data.get('image_url'):
                cursor.execute("""
                    INSERT INTO product_images (
                        product_id, image_url, alt_text, is_primary, display_order
                    ) VALUES (%s, %s, %s, TRUE, 1)
                """, (product_id, product_data['image_url'], product_data['name']))
            
            connection.commit()
            
            # Fetch and return created product
            return self.get_seller_product(seller_id, product_id)
            
        except Error as e:
            if connection.is_connected():
                connection.rollback()
            print(f"Error creating product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== UPDATE PRODUCT ====================
    
    def update_product(self, seller_id: int, product_id: int, product_data: dict) -> Dict[str, Any]:
        """Update existing product"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        # Verify ownership
        if not self.verify_product_ownership(seller_id, product_id):
            return {'success': False, 'message': 'Product not found or access denied'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Build dynamic update query
            update_fields = []
            params = []
            
            # Map of allowed fields to update
            allowed_fields = {
                'name': 'name = %s',
                'slug': 'slug = %s',
                'description': 'description = %s',
                'short_description': 'short_description = %s',
                'price': 'price = %s',
                'compare_at_price': 'compare_at_price = %s',
                'category_id': 'category_id = %s',
                'sku': 'sku = %s',
                'quantity_in_stock': 'quantity_in_stock = %s',
                'weight': 'weight = %s',
                'is_featured': 'is_featured = %s',
                'is_active': 'is_active = %s'
            }
            
            for field, sql in allowed_fields.items():
                if field in product_data:
                    update_fields.append(sql)
                    params.append(product_data[field])
            
            if not update_fields:
                return {'success': False, 'message': 'No fields to update'}
            
            # Check if slug is being updated and already exists
            if 'slug' in product_data:
                cursor.execute(
                    "SELECT id FROM products WHERE slug = %s AND id != %s", 
                    (product_data['slug'], product_id)
                )
                if cursor.fetchone():
                    return {'success': False, 'message': 'Product slug already exists'}
            
            # Check if SKU is being updated and already exists
            if 'sku' in product_data and product_data['sku']:
                cursor.execute(
                    "SELECT id FROM products WHERE sku = %s AND id != %s", 
                    (product_data['sku'], product_id)
                )
                if cursor.fetchone():
                    return {'success': False, 'message': 'SKU already exists'}
            
            # Add updated_at
            update_fields.append('updated_at = NOW()')
            
            # Add product_id to params
            params.append(product_id)
            
            # Execute update
            update_query = f"""
                UPDATE products 
                SET {', '.join(update_fields)}
                WHERE id = %s AND seller_id = {seller_id}
            """
            
            cursor.execute(update_query, params)
            
            # Update product image if provided
            if 'image_url' in product_data and product_data['image_url']:
                # Check if primary image exists
                cursor.execute("""
                    SELECT id FROM product_images 
                    WHERE product_id = %s AND is_primary = TRUE
                """, (product_id,))
                
                existing_image = cursor.fetchone()
                
                if existing_image:
                    # Update existing primary image
                    cursor.execute("""
                        UPDATE product_images 
                        SET image_url = %s, alt_text = %s
                        WHERE id = %s
                    """, (product_data['image_url'], product_data.get('name', ''), existing_image['id']))
                else:
                    # Insert new primary image
                    cursor.execute("""
                        INSERT INTO product_images (
                            product_id, image_url, alt_text, is_primary, display_order
                        ) VALUES (%s, %s, %s, TRUE, 1)
                    """, (product_id, product_data['image_url'], product_data.get('name', '')))
            
            connection.commit()
            
            # Fetch and return updated product
            return self.get_seller_product(seller_id, product_id)
            
        except Error as e:
            if connection.is_connected():
                connection.rollback()
            print(f"Error updating product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== DELETE PRODUCT ====================
    
    def delete_product(self, seller_id: int, product_id: int) -> Dict[str, Any]:
        """Delete product (soft delete by setting is_active to False)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        # Verify ownership
        if not self.verify_product_ownership(seller_id, product_id):
            return {'success': False, 'message': 'Product not found or access denied'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if product is in any pending/processing orders
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s 
                AND o.status IN ('pending', 'processing')
            """, (product_id,))
            
            result = cursor.fetchone()
            if result['count'] > 0:
                return {
                    'success': False, 
                    'message': 'Cannot delete product with pending orders. Please deactivate instead.'
                }
            
            # Soft delete: set is_active to False
            cursor.execute("""
                UPDATE products 
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s AND seller_id = %s
            """, (product_id, seller_id))
            
            connection.commit()
            
            return {
                'success': True, 
                'message': 'Product deleted successfully',
                'product_id': product_id
            }
            
        except Error as e:
            if connection.is_connected():
                connection.rollback()
            print(f"Error deleting product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== HARD DELETE (ADMIN ONLY) ====================
    
    def hard_delete_product(self, seller_id: int, product_id: int) -> Dict[str, Any]:
        """Permanently delete product and all related data"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        # Verify seller
        if not self.verify_seller(seller_id):
            return {'success': False, 'message': 'User is not an active seller'}
        
        # Verify ownership
        if not self.verify_product_ownership(seller_id, product_id):
            return {'success': False, 'message': 'Product not found or access denied'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if product is in any orders
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM order_items
                WHERE product_id = %s
            """, (product_id,))
            
            result = cursor.fetchone()
            if result['count'] > 0:
                return {
                    'success': False, 
                    'message': 'Cannot permanently delete product with order history'
                }
            
            # Delete product (cascades to images, variants, tags due to foreign keys)
            cursor.execute("""
                DELETE FROM products 
                WHERE id = %s AND seller_id = %s
            """, (product_id, seller_id))
            
            connection.commit()
            
            return {
                'success': True, 
                'message': 'Product permanently deleted',
                'product_id': product_id
            }
            
        except Error as e:
            if connection.is_connected():
                connection.rollback()
            print(f"Error hard deleting product: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()