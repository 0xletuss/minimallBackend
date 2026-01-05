from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import mysql.connector
from mysql.connector import Error
import os

# Enums
class SellerStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class BusinessType(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"

class PayoutSchedule(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

# Pydantic Request/Response Models
class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image: Optional[str] = Field(None, max_length=500)
    social_handle: Optional[str] = Field(None, max_length=100)

class ProfileResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    is_seller: bool
    seller_status: Optional[str]
    bio: Optional[str]
    profile_image: Optional[str]
    social_handle: Optional[str]
    created_at: datetime

class UserStatistics(BaseModel):
    purchased_products: int = 0
    total_spent: float = 0.00
    loyalty_points: int = 0
    available_coupons: int = 0
    wishlist_count: int = 0
    last_purchase_date: Optional[datetime] = None

class SellerApplicationCreate(BaseModel):
    store_name: str = Field(..., min_length=3, max_length=150)
    business_type: BusinessType
    business_description: Optional[str] = Field(None, max_length=1000)
    id_document_url: Optional[str] = Field(None, max_length=500)
    business_document_url: Optional[str] = Field(None, max_length=500)

    @validator('store_name')
    def validate_store_name(cls, v):
        if not v.strip():
            raise ValueError('Store name cannot be empty')
        return v.strip()

class SellerApplicationResponse(BaseModel):
    id: int
    user_id: int
    store_name: str
    business_type: str
    business_description: Optional[str]
    status: str
    rejection_reason: Optional[str]
    applied_at: datetime
    reviewed_at: Optional[datetime]

class SellerProfileCreate(BaseModel):
    store_name: str = Field(..., min_length=3, max_length=150)
    store_description: Optional[str] = Field(None, max_length=1000)
    store_logo: Optional[str] = Field(None, max_length=500)
    store_banner: Optional[str] = Field(None, max_length=500)
    business_type: BusinessType = BusinessType.INDIVIDUAL
    bank_account_name: Optional[str] = Field(None, max_length=150)
    bank_account_number: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    payout_schedule: PayoutSchedule = PayoutSchedule.WEEKLY

class SellerProfileUpdate(BaseModel):
    store_name: Optional[str] = Field(None, min_length=3, max_length=150)
    store_description: Optional[str] = Field(None, max_length=1000)
    store_logo: Optional[str] = Field(None, max_length=500)
    store_banner: Optional[str] = Field(None, max_length=500)
    bank_account_name: Optional[str] = Field(None, max_length=150)
    bank_account_number: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    payout_schedule: Optional[PayoutSchedule] = None

class SellerProfileResponse(BaseModel):
    id: int
    user_id: int
    store_name: str
    store_description: Optional[str]
    store_logo: Optional[str]
    store_banner: Optional[str]
    business_type: str
    total_sales: float
    total_orders: int
    rating: float
    total_reviews: int
    commission_rate: float
    payout_schedule: str
    created_at: datetime

class TransactionItem(BaseModel):
    order_id: int
    order_number: str
    purchased_date: datetime
    total_amount: float
    status: str

class RecentTransactionsResponse(BaseModel):
    transactions: List[TransactionItem]
    total_count: int

class UserCouponResponse(BaseModel):
    id: int
    code: str
    description: Optional[str]
    discount_type: str
    discount_value: float
    min_purchase_amount: float
    valid_until: datetime
    is_used: bool

class ProfileDashboardResponse(BaseModel):
    profile: ProfileResponse
    statistics: UserStatistics
    recent_transactions: List[TransactionItem]
    available_coupons: List[UserCouponResponse]
    seller_profile: Optional[SellerProfileResponse] = None


# ==================== ProfileModel Class ====================
class ProfileModel:
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
    
    # ==================== PROFILE METHODS ====================
    
    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user profile"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, email, full_name, phone, is_seller, 
                       seller_status, bio, profile_image, social_handle, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            return {'success': True, 'data': user}
            
        except Error as e:
            print(f"Error getting profile: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_user_profile(self, user_id: int, profile_data: dict) -> Dict[str, Any]:
        """Update user profile - allows setting fields to null"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Build dynamic update query
            update_fields = []
            params = []
            
            # Only update fields that are present in profile_data
            # Allow None values to clear fields
            if 'bio' in profile_data:
                update_fields.append("bio = %s")
                params.append(profile_data['bio'])
            
            if 'profile_image' in profile_data:
                update_fields.append("profile_image = %s")
                params.append(profile_data['profile_image'])
            
            if 'social_handle' in profile_data:
                update_fields.append("social_handle = %s")
                params.append(profile_data['social_handle'])
            
            if not update_fields:
                return {'success': False, 'message': 'No fields to update'}
            
            params.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            cursor.execute(query, params)
            connection.commit()
            
            if cursor.rowcount == 0:
                return {'success': False, 'message': 'User not found or no changes made'}
            
            # Fetch updated profile
            cursor.execute("""
                SELECT id, email, full_name, phone, is_seller, 
                       seller_status, bio, profile_image, social_handle, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            updated_profile = cursor.fetchone()
            
            if not updated_profile:
                return {'success': False, 'message': 'Failed to fetch updated profile'}
            
            return {'success': True, 'data': updated_profile}
            
        except Error as e:
            print(f"Error updating profile: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get or create user statistics"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT purchased_products, total_spent, loyalty_points, 
                       available_coupons, wishlist_count, last_purchase_date
                FROM user_statistics
                WHERE user_id = %s
            """, (user_id,))
            
            stats = cursor.fetchone()
            
            if not stats:
                # Create default statistics
                cursor.execute("""
                    INSERT INTO user_statistics (user_id) VALUES (%s)
                """, (user_id,))
                connection.commit()
                stats = {
                    'purchased_products': 0,
                    'total_spent': 0.00,
                    'loyalty_points': 0,
                    'available_coupons': 0,
                    'wishlist_count': 0,
                    'last_purchase_date': None
                }
            
            return {'success': True, 'data': stats}
            
        except Error as e:
            print(f"Error getting statistics: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_recent_transactions(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get recent transactions"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    o.id as order_id,
                    o.order_number,
                    o.created_at as purchased_date,
                    o.total as total_amount,
                    o.status
                FROM orders o
                WHERE o.user_id = %s
                ORDER BY o.created_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            transactions = cursor.fetchall() or []
            
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM orders
                WHERE user_id = %s
            """, (user_id,))
            
            total = cursor.fetchone()['total']
            
            return {
                'success': True,
                'data': {
                    'transactions': transactions,
                    'total_count': total
                }
            }
            
        except Error as e:
            print(f"Error getting transactions: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_user_coupons(self, user_id: int) -> Dict[str, Any]:
        """Get user's available coupons"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    uc.id,
                    c.code,
                    c.description,
                    c.discount_type,
                    c.discount_value,
                    c.min_purchase_amount,
                    c.valid_until,
                    uc.is_used
                FROM user_coupons uc
                JOIN coupons c ON uc.coupon_id = c.id
                WHERE uc.user_id = %s 
                AND uc.is_used = FALSE
                AND c.valid_until > NOW()
                AND c.is_active = TRUE
                ORDER BY c.valid_until ASC
            """, (user_id,))
            
            coupons = cursor.fetchall() or []
            return {'success': True, 'data': coupons}
            
        except Error as e:
            print(f"Error getting coupons: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_profile_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get complete profile dashboard"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get user profile
            cursor.execute("""
                SELECT id, email, full_name, phone, is_seller, 
                       seller_status, bio, profile_image, social_handle, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            profile = cursor.fetchone()
            
            if not profile:
                return {'success': False, 'message': 'User not found'}
            
            # Get or create statistics
            cursor.execute("""
                SELECT purchased_products, total_spent, loyalty_points, 
                       available_coupons, wishlist_count, last_purchase_date
                FROM user_statistics
                WHERE user_id = %s
            """, (user_id,))
            statistics = cursor.fetchone()
            
            if not statistics:
                cursor.execute("""
                    INSERT INTO user_statistics (user_id) VALUES (%s)
                """, (user_id,))
                connection.commit()
                statistics = {
                    'purchased_products': 0,
                    'total_spent': 0.00,
                    'loyalty_points': 0,
                    'available_coupons': 0,
                    'wishlist_count': 0,
                    'last_purchase_date': None
                }
            
            # Get recent transactions
            cursor.execute("""
                SELECT 
                    o.id as order_id,
                    o.order_number,
                    o.created_at as purchased_date,
                    o.total as total_amount,
                    o.status
                FROM orders o
                WHERE o.user_id = %s
                ORDER BY o.created_at DESC
                LIMIT 5
            """, (user_id,))
            transactions = cursor.fetchall() or []
            
            # Get available coupons
            cursor.execute("""
                SELECT 
                    uc.id,
                    c.code,
                    c.description,
                    c.discount_type,
                    c.discount_value,
                    c.min_purchase_amount,
                    c.valid_until,
                    uc.is_used
                FROM user_coupons uc
                JOIN coupons c ON uc.coupon_id = c.id
                WHERE uc.user_id = %s 
                AND uc.is_used = FALSE
                AND c.valid_until > NOW()
                AND c.is_active = TRUE
                ORDER BY c.valid_until ASC
            """, (user_id,))
            coupons = cursor.fetchall() or []
            
            # Get seller profile if applicable
            seller_profile = None
            if profile.get('is_seller'):
                cursor.execute("""
                    SELECT id, user_id, store_name, store_description, store_logo, 
                           store_banner, business_type, total_sales, total_orders, 
                           rating, total_reviews, commission_rate, payout_schedule, created_at
                    FROM seller_profiles
                    WHERE user_id = %s
                """, (user_id,))
                seller_profile = cursor.fetchone()
            
            return {
                'success': True,
                'data': {
                    'profile': profile,
                    'statistics': statistics,
                    'recent_transactions': transactions,
                    'available_coupons': coupons,
                    'seller_profile': seller_profile
                }
            }
            
        except Error as e:
            print(f"Error getting dashboard: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== SELLER APPLICATION METHODS ====================
    
    def create_seller_application(self, user_id: int, application_data: dict) -> Dict[str, Any]:
        """Submit seller application"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if user is already a seller
            cursor.execute("SELECT is_seller FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            if user['is_seller']:
                return {'success': False, 'message': 'You are already a seller'}
            
            # Check for pending application
            cursor.execute("""
                SELECT id FROM seller_applications 
                WHERE user_id = %s AND status = 'pending'
            """, (user_id,))
            
            if cursor.fetchone():
                return {'success': False, 'message': 'You already have a pending application'}
            
            # Create application
            cursor.execute("""
                INSERT INTO seller_applications 
                (user_id, store_name, business_type, business_description, 
                 id_document_url, business_document_url, status, applied_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW())
            """, (
                user_id,
                application_data['store_name'],
                application_data['business_type'],
                application_data.get('business_description'),
                application_data.get('id_document_url'),
                application_data.get('business_document_url')
            ))
            
            connection.commit()
            application_id = cursor.lastrowid
            
            # Fetch created application
            cursor.execute("""
                SELECT id, user_id, store_name, business_type, business_description,
                       status, rejection_reason, applied_at, reviewed_at
                FROM seller_applications
                WHERE id = %s
            """, (application_id,))
            
            application = cursor.fetchone()
            return {'success': True, 'data': application}
            
        except Error as e:
            print(f"Error creating application: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_seller_application_status(self, user_id: int) -> Dict[str, Any]:
        """Get seller application status"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, user_id, store_name, business_type, business_description,
                       status, rejection_reason, applied_at, reviewed_at
                FROM seller_applications
                WHERE user_id = %s
                ORDER BY applied_at DESC
                LIMIT 1
            """, (user_id,))
            
            application = cursor.fetchone()
            if not application:
                return {'success': False, 'message': 'No application found'}
            
            return {'success': True, 'data': application}
            
        except Error as e:
            print(f"Error getting application: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # ==================== SELLER PROFILE METHODS ====================
    
    def get_seller_profile(self, user_id: int) -> Dict[str, Any]:
        """Get seller profile - auto-create if missing but user is approved seller"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if user is a seller
            cursor.execute("SELECT is_seller FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            if not user['is_seller']:
                return {'success': False, 'message': 'You are not a seller'}
            
            # Try to get seller profile
            cursor.execute("""
                SELECT id, user_id, store_name, store_description, store_logo, 
                       store_banner, business_type, total_sales, total_orders, 
                       rating, total_reviews, commission_rate, payout_schedule, created_at
                FROM seller_profiles
                WHERE user_id = %s
            """, (user_id,))
            
            profile = cursor.fetchone()
            
            # If profile doesn't exist but user is marked as seller, try to create from approved application
            if not profile:
                cursor.execute("""
                    SELECT store_name, business_type, business_description
                    FROM seller_applications
                    WHERE user_id = %s AND status = 'approved'
                    ORDER BY applied_at DESC
                    LIMIT 1
                """, (user_id,))
                
                app_data = cursor.fetchone()
                
                if app_data:
                    # Create seller profile from approved application
                    cursor.execute("""
                        INSERT INTO seller_profiles 
                        (user_id, store_name, business_type, store_description, 
                         total_sales, total_orders, rating, total_reviews, 
                         commission_rate, payout_schedule)
                        VALUES (%s, %s, %s, %s, 0.00, 0, 0.0, 0, 10.00, 'weekly')
                    """, (
                        user_id,
                        app_data['store_name'],
                        app_data['business_type'],
                        app_data.get('business_description', '')
                    ))
                    
                    connection.commit()
                    
                    # Fetch the newly created profile
                    cursor.execute("""
                        SELECT id, user_id, store_name, store_description, store_logo, 
                               store_banner, business_type, total_sales, total_orders, 
                               rating, total_reviews, commission_rate, payout_schedule, created_at
                        FROM seller_profiles
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    profile = cursor.fetchone()
                else:
                    return {'success': False, 'message': 'Seller profile not found'}
            
            if not profile:
                return {'success': False, 'message': 'Seller profile not found'}
            
            return {'success': True, 'data': profile}
            
        except Error as e:
            print(f"Error getting seller profile: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_seller_profile(self, user_id: int, profile_data: dict) -> Dict[str, Any]:
        """Update seller profile - allows setting fields to null"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if user is a seller
            cursor.execute("SELECT is_seller FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            if not user['is_seller']:
                return {'success': False, 'message': 'You are not a seller'}
            
            # Build dynamic update query
            update_fields = []
            params = []
            
            # Allow all fields to be updated, including setting to null
            allowed_fields = [
                'store_name', 'store_description', 'store_logo', 'store_banner',
                'bank_account_name', 'bank_account_number', 'bank_name', 'payout_schedule'
            ]
            
            for field in allowed_fields:
                if field in profile_data:
                    update_fields.append(f"{field} = %s")
                    params.append(profile_data[field])
            
            if not update_fields:
                return {'success': False, 'message': 'No fields to update'}
            
            params.append(user_id)
            
            query = f"""
                UPDATE seller_profiles 
                SET {', '.join(update_fields)}
                WHERE user_id = %s
            """
            
            cursor.execute(query, params)
            connection.commit()
            
            if cursor.rowcount == 0:
                return {'success': False, 'message': 'Seller profile not found or no changes made'}
            
            # Fetch updated profile
            cursor.execute("""
                SELECT id, user_id, store_name, store_description, store_logo, 
                       store_banner, business_type, total_sales, total_orders, 
                       rating, total_reviews, commission_rate, payout_schedule, created_at
                FROM seller_profiles
                WHERE user_id = %s
            """, (user_id,))
            
            updated_profile = cursor.fetchone()
            
            if not updated_profile:
                return {'success': False, 'message': 'Failed to fetch updated profile'}
            
            return {'success': True, 'data': updated_profile}
            
        except Error as e:
            print(f"Error updating seller profile: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def create_seller_profile_from_application(self, user_id: int) -> Dict[str, Any]:
        """Create seller profile from approved application (manual trigger)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if seller profile already exists
            cursor.execute("""
                SELECT id FROM seller_profiles WHERE user_id = %s
            """, (user_id,))
            
            existing_profile = cursor.fetchone()
            if existing_profile:
                # Profile exists, just fetch and return it
                cursor.execute("""
                    SELECT id, user_id, store_name, store_description, store_logo, 
                           store_banner, business_type, total_sales, total_orders, 
                           rating, total_reviews, commission_rate, payout_schedule, created_at
                    FROM seller_profiles
                    WHERE user_id = %s
                """, (user_id,))
                
                profile = cursor.fetchone()
                return {
                    'success': True,
                    'data': profile,
                    'message': 'Seller profile already exists'
                }
            
            # Check if user has approved application
            cursor.execute("""
                SELECT store_name, business_type, business_description
                FROM seller_applications
                WHERE user_id = %s AND status = 'approved'
                ORDER BY applied_at DESC
                LIMIT 1
            """, (user_id,))
            
            app_data = cursor.fetchone()
            
            if not app_data:
                return {
                    'success': False, 
                    'message': 'No approved seller application found'
                }
            
            # Update user to be a seller
            cursor.execute("""
                UPDATE users 
                SET is_seller = TRUE, seller_status = 'active'
                WHERE id = %s
            """, (user_id,))
            
            # Create seller profile
            cursor.execute("""
                INSERT INTO seller_profiles 
                (user_id, store_name, business_type, store_description, 
                 total_sales, total_orders, rating, total_reviews, 
                 commission_rate, payout_schedule)
                VALUES (%s, %s, %s, %s, 0.00, 0, 0.0, 0, 10.00, 'weekly')
            """, (
                user_id,
                app_data['store_name'],
                app_data['business_type'],
                app_data.get('business_description', '')
            ))
            
            connection.commit()
            
            # Fetch the created profile
            cursor.execute("""
                SELECT id, user_id, store_name, store_description, store_logo, 
                       store_banner, business_type, total_sales, total_orders, 
                       rating, total_reviews, commission_rate, payout_schedule, created_at
                FROM seller_profiles
                WHERE user_id = %s
            """, (user_id,))
            
            profile = cursor.fetchone()
            
            return {
                'success': True,
                'data': profile,
                'message': 'Seller profile created successfully'
            }
            
        except Error as e:
            if connection:
                connection.rollback()
            print(f"Error creating seller profile: {e}")
            return {
                'success': False, 
                'message': f'Error creating seller profile: {str(e)}'
            }
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def approve_seller_application(self, application_id: int, user_id: int) -> Dict[str, Any]:
        """Approve seller application and create profile (for admin use)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get application data
            cursor.execute("""
                SELECT user_id, store_name, business_type, business_description, status
                FROM seller_applications
                WHERE id = %s
            """, (application_id,))
            
            application = cursor.fetchone()
            
            if not application:
                return {'success': False, 'message': 'Application not found'}
            
            if application['status'] == 'approved':
                return {'success': False, 'message': 'Application already approved'}
            
            app_user_id = application['user_id']
            
            # Update application status
            cursor.execute("""
                UPDATE seller_applications 
                SET status = 'approved', reviewed_at = NOW()
                WHERE id = %s
            """, (application_id,))
            
            # Update user to be a seller
            cursor.execute("""
                UPDATE users 
                SET is_seller = TRUE, seller_status = 'active'
                WHERE id = %s
            """, (app_user_id,))
            
            # Create seller profile
            cursor.execute("""
                INSERT INTO seller_profiles 
                (user_id, store_name, business_type, store_description, 
                 total_sales, total_orders, rating, total_reviews, 
                 commission_rate, payout_schedule)
                VALUES (%s, %s, %s, %s, 0.00, 0, 0.0, 0, 10.00, 'weekly')
                ON DUPLICATE KEY UPDATE
                    store_name = VALUES(store_name),
                    business_type = VALUES(business_type),
                    store_description = VALUES(store_description)
            """, (
                app_user_id,
                application['store_name'],
                application['business_type'],
                application.get('business_description', '')
            ))
            
            connection.commit()
            
            return {
                'success': True,
                'message': 'Seller application approved and profile created'
            }
            
        except Error as e:
            if connection:
                connection.rollback()
            print(f"Error approving application: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()