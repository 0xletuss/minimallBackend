import mysql.connector
from datetime import datetime, timedelta
import os

class OTPModel:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME')
        }
    
    def get_connection(self):
        return mysql.connector.connect(**self.db_config)
    
    def create_otp_table(self):
        """Create OTP table if it doesn't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def store_otp(self, email: str, otp_code: str, purpose: str = 'registration') -> dict:
        """Store OTP in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete old unverified OTPs for this email and purpose
            cursor.execute("""
                DELETE FROM otp_codes 
                WHERE email = %s AND purpose = %s AND verified = FALSE
            """, (email, purpose))
            
            # Set expiration (10 minutes from now)
            expires_at = datetime.now() + timedelta(minutes=10)
            
            cursor.execute("""
                INSERT INTO otp_codes (email, otp_code, purpose, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (email, otp_code, purpose, expires_at))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"success": True, "message": "OTP stored successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def verify_otp(self, email: str, otp_code: str, purpose: str = 'registration') -> dict:
        """Verify OTP code"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
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
                cursor.close()
                conn.close()
                return {"success": False, "message": "Invalid or expired OTP"}
            
            # Mark OTP as verified
            cursor.execute("""
                UPDATE otp_codes 
                SET verified = TRUE 
                WHERE id = %s
            """, (otp_record['id'],))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"success": True, "message": "OTP verified successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def cleanup_expired_otps(self):
        """Remove expired OTPs (call this periodically)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM otp_codes 
                WHERE expires_at < NOW()
            """)
            
            conn.commit()
            deleted_count = cursor.rowcount
            cursor.close()
            conn.close()
            
            return {"success": True, "deleted": deleted_count}
        except Exception as e:
            return {"success": False, "message": str(e)}