import mysql.connector
from mysql.connector import Error
from passlib.context import CryptContext
import os
from datetime import datetime
from typing import Optional, Dict, Any

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthModel:
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
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_user(
        self, 
        email: str, 
        password: str, 
        full_name: str, 
        phone: Optional[str] = None, 
        role: str = 'customer'
    ) -> Dict[str, Any]:
        """Create a new user account"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {'success': False, 'message': 'Email already registered'}
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Insert user
            query = """
                INSERT INTO users (email, password_hash, full_name, phone, role) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (email, password_hash, full_name, phone, role))
            connection.commit()
            
            user_id = cursor.lastrowid
            
            return {
                'success': True, 
                'message': 'User created successfully',
                'user_id': user_id
            }
            
        except Error as e:
            print(f"Error creating user: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def verify_user(self, email: str, password: str) -> Dict[str, Any]:
        """Verify user credentials"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT id, email, password_hash, full_name, phone, role, is_active 
                FROM users WHERE email = %s
            """
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'message': 'Invalid credentials'}
            
            if not user['is_active']:
                return {'success': False, 'message': 'Account is deactivated'}
            
            # Verify password
            if self.verify_password(password, user['password_hash']):
                # Update last login
                update_query = "UPDATE users SET last_login = %s WHERE id = %s"
                cursor.execute(update_query, (datetime.now(), user['id']))
                connection.commit()
                
                # Remove password_hash from return data
                user.pop('password_hash', None)
                
                return {
                    'success': True,
                    'message': 'Login successful',
                    'user': user
                }
            else:
                return {'success': False, 'message': 'Invalid credentials'}
                
        except Error as e:
            print(f"Error verifying user: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, email, full_name, phone, role, is_active, 
                       email_verified, created_at, last_login 
                FROM users WHERE id = %s
            """
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            return user
            
        except Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, email, full_name, phone, role, is_active, 
                       email_verified, created_at, last_login 
                FROM users WHERE email = %s
            """
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            return user
            
        except Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()