import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import random
import string

class BrevoEmailService:
    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str):
        """Send email via Brevo"""
        try:
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email, "name": to_name}],
                sender={"email": "noreply@yourdomain.com", "name": "Your E-commerce Store"},
                subject=subject,
                html_content=html_content
            )
            
            response = self.api_instance.send_transac_email(send_smtp_email)
            return {"success": True, "message_id": response.message_id}
        except ApiException as e:
            print(f"Brevo API Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def send_otp_email(self, email: str, name: str, otp: str, purpose: str = "verification"):
        """Send OTP email for registration or login"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0;">Your Verification Code</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p style="font-size: 16px; color: #333;">Hi {name},</p>
                    <p style="font-size: 14px; color: #666;">Your OTP code for {purpose} is:</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <h2 style="color: #667eea; font-size: 32px; letter-spacing: 8px; margin: 0;">{otp}</h2>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">This code will expire in <strong>10 minutes</strong>.</p>
                    <p style="font-size: 14px; color: #666;">If you didn't request this code, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #999; text-align: center;">
                        This is an automated message, please do not reply.
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(
            to_email=email,
            to_name=name,
            subject=f"Your OTP Code - {otp}",
            html_content=html_content
        )
    
    def send_welcome_email(self, email: str, name: str):
        """Send welcome email after successful registration"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0;">Welcome to Our Store! 🎉</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p style="font-size: 16px; color: #333;">Hi {name},</p>
                    <p style="font-size: 14px; color: #666;">Thank you for joining our e-commerce platform!</p>
                    <p style="font-size: 14px; color: #666;">Your account has been successfully verified and you can now start shopping.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="https://yourstore.com" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Start Shopping</a>
                    </div>
                    
                    <p style="font-size: 12px; color: #999; text-align: center; margin-top: 30px;">
                        Need help? Contact us at support@yourstore.com
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(
            to_email=email,
            to_name=name,
            subject="Welcome to Our Store!",
            html_content=html_content
        )

# Create singleton instance
brevo_service = BrevoEmailService()