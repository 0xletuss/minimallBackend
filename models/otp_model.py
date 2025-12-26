import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional


class OTPModel:
    def __init__(self):
        """Initialize OTP Model with consistent database configuration"""
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'railway'),
            'port': int(os.getenv('MYSQL_PORT', 3306))
        }
    
    def get_connection(self):
        """Get database connection with error handling"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    def create_otp_table(self) -> Dict[str, Any]:
        """Create OTP table if it doesn't exist"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS otp_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    otp_code VARCHAR(10) NOT NULL,
                    purpose ENUM('registration', 'login', 'password_reset') NOT NULL,
                    expires_at DATETIME NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_email_otp (email, otp_code),
                    INDEX idx_expires (expires_at)
                )
            """)
            
            connection.commit()
            return {'success': True, 'message': 'OTP table created successfully'}
            
        except Error as e:
            print(f"Error creating OTP table: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def store_otp(
        self, 
        email: str, 
        otp_code: str, 
        purpose: str = 'registration'
    ) -> Dict[str, Any]:
        """Store OTP in database with 10-minute expiration"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor()
            
            # Delete old unverified OTPs for this email and purpose
            cursor.execute("""
                DELETE FROM otp_codes 
                WHERE email = %s AND purpose = %s AND verified = FALSE
            """, (email, purpose))
            
            # Set expiration (10 minutes from now)
            expires_at = datetime.now() + timedelta(minutes=10)
            
            # Insert new OTP
            cursor.execute("""
                INSERT INTO otp_codes (email, otp_code, purpose, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (email, otp_code, purpose, expires_at))
            
            connection.commit()
            
            return {
                'success': True, 
                'message': 'OTP stored successfully',
                'expires_at': expires_at.isoformat()
            }
            
        except Error as e:
            print(f"Error storing OTP: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def verify_otp(
        self, 
        email: str, 
        otp_code: str, 
        purpose: str = 'registration'
    ) -> Dict[str, Any]:
        """Verify OTP code and mark as used"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if OTP exists and is valid
            cursor.execute("""
                SELECT * FROM otp_codes 
                WHERE email = %s 
                AND otp_code = %s 
                AND purpose = %s 
                AND verified = FALSE 
                AND expires_at > NOW()
                ORDER BY created_at DESC 
                LIMIT 1
            """, (email, otp_code, purpose))
            
            otp_record = cursor.fetchone()
            
            if not otp_record:
                return {
                    'success': False, 
                    'message': 'Invalid or expired OTP'
                }
            
            # Mark OTP as verified
            cursor.execute("""
                UPDATE otp_codes 
                SET verified = TRUE 
                WHERE id = %s
            """, (otp_record['id'],))
            
            connection.commit()
            
            return {
                'success': True, 
                'message': 'OTP verified successfully',
                'email': email
            }
            
        except Error as e:
            print(f"Error verifying OTP: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def check_otp_exists(
        self, 
        email: str, 
        purpose: str = 'registration'
    ) -> Dict[str, Any]:
        """Check if valid OTP exists for email and purpose"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, expires_at FROM otp_codes 
                WHERE email = %s 
                AND purpose = %s 
                AND verified = FALSE 
                AND expires_at > NOW()
                ORDER BY created_at DESC 
                LIMIT 1
            """, (email, purpose))
            
            otp_record = cursor.fetchone()
            
            if otp_record:
                return {
                    'success': True,
                    'exists': True,
                    'expires_at': otp_record['expires_at'].isoformat()
                }
            else:
                return {
                    'success': True,
                    'exists': False
                }
                
        except Error as e:
            print(f"Error checking OTP: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def cleanup_expired_otps(self) -> Dict[str, Any]:
        """Remove expired OTPs (call this periodically via cron job)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor()
            
            cursor.execute("""
                DELETE FROM otp_codes 
                WHERE expires_at < NOW()
            """)
            
            connection.commit()
            deleted_count = cursor.rowcount
            
            return {
                'success': True, 
                'deleted': deleted_count,
                'message': f'Cleaned up {deleted_count} expired OTPs'
            }
            
        except Error as e:
            print(f"Error cleaning up OTPs: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def invalidate_otp(
        self, 
        email: str, 
        purpose: str = 'registration'
    ) -> Dict[str, Any]:
        """Invalidate all OTPs for a specific email and purpose"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor()
            
            cursor.execute("""
                UPDATE otp_codes 
                SET verified = TRUE 
                WHERE email = %s 
                AND purpose = %s 
                AND verified = FALSE
            """, (email, purpose))
            
            connection.commit()
            
            return {
                'success': True, 
                'message': 'OTPs invalidated successfully'
            }
            
        except Error as e:
            print(f"Error invalidating OTPs: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_otp_attempts(
        self, 
        email: str, 
        purpose: str = 'registration',
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get count of OTP attempts within time window (for rate limiting)"""
        connection = self.get_connection()
        if not connection:
            return {'success': False, 'message': 'Database connection failed'}
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            time_threshold = datetime.now() - timedelta(minutes=time_window_minutes)
            
            cursor.execute("""
                SELECT COUNT(*) as attempt_count
                FROM otp_codes 
                WHERE email = %s 
                AND purpose = %s 
                AND created_at > %s
            """, (email, purpose, time_threshold))
            
            result = cursor.fetchone()
            
            return {
                'success': True,
                'attempts': result['attempt_count'] if result else 0,
                'time_window_minutes': time_window_minutes
            }
            
        except Error as e:
            print(f"Error getting OTP attempts: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()