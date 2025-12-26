import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import random
import string
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrevoEmailService:
    def __init__(self):
        api_key = os.getenv('BREVO_API_KEY')
        if not api_key:
            logger.error("BREVO_API_KEY environment variable not set!")
            raise ValueError("BREVO_API_KEY is required")
        
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        # Use your verified Gmail sender
        self.sender_email = os.getenv('BREVO_GMAIL_SENDER', 'Ramoscarlosjaimeroa@gmail.com')
        self.sender_name = os.getenv('BREVO_SENDER_NAME', 'Minimall Store')
        
        logger.info(f"✅ Brevo service initialized")
        logger.info(f"📧 Sender: {self.sender_email}")
        logger.info(f"👤 Name: {self.sender_name}")
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        otp = ''.join(random.choices(string.digits, k=length))
        logger.info(f"🔐 Generated OTP: {otp}")
        return otp
    
    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str):
        """Send email via Brevo with detailed error logging"""
        try:
            logger.info(f"📧 =================================")
            logger.info(f"📧 Sending email to: {to_email}")
            logger.info(f"📤 From: {self.sender_email}")
            logger.info(f"📝 Subject: {subject}")
            logger.info(f"📧 =================================")
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email, "name": to_name}],
                sender={"email": self.sender_email, "name": self.sender_name},
                subject=subject,
                html_content=html_content
            )
            
            response = self.api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"✅ =================================")
            logger.info(f"✅ EMAIL SENT SUCCESSFULLY!")
            logger.info(f"✅ Message ID: {response.message_id}")
            logger.info(f"✅ To: {to_email}")
            logger.info(f"✅ =================================")
            
            return {
                "success": True, 
                "message_id": response.message_id,
                "message": "Email sent successfully",
                "to_email": to_email
            }
            
        except ApiException as e:
            error_body = None
            error_message = str(e)
            
            try:
                import json
                error_body = json.loads(e.body)
                error_message = error_body.get('message', str(e))
            except:
                pass
            
            logger.error(f"❌ =================================")
            logger.error(f"❌ BREVO API ERROR!")
            logger.error(f"❌ Status: {e.status}")
            logger.error(f"❌ Reason: {e.reason}")
            logger.error(f"❌ Message: {error_message}")
            logger.error(f"❌ To: {to_email}")
            logger.error(f"❌ From: {self.sender_email}")
            if error_body:
                logger.error(f"❌ Full error: {error_body}")
            logger.error(f"❌ =================================")
            
            return {
                "success": False, 
                "error": error_message,
                "status": e.status,
                "to_email": to_email
            }
        
        except Exception as e:
            logger.error(f"❌ =================================")
            logger.error(f"❌ UNEXPECTED ERROR!")
            logger.error(f"❌ Error: {str(e)}")
            logger.error(f"❌ Type: {type(e).__name__}")
            logger.error(f"❌ =================================")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "success": False, 
                "error": f"Unexpected error: {str(e)}"
            }
    
    def send_otp_email(self, email: str, name: str, otp: str, purpose: str = "verification"):
        """Send OTP email for registration or login"""
        logger.info(f"🔐 =================================")
        logger.info(f"🔐 PREPARING OTP EMAIL")
        logger.info(f"🔐 To: {email}")
        logger.info(f"🔐 Name: {name}")
        logger.info(f"🔐 OTP: {otp}")
        logger.info(f"🔐 Purpose: {purpose}")
        logger.info(f"🔐 =================================")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden;">
                <tr>
                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">🔐 Your Verification Code</h1>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 40px 30px;">
                        <p style="font-size: 16px; color: #333; margin: 0 0 20px 0;">Hi {name},</p>
                        <p style="font-size: 14px; color: #666; margin: 0 0 20px 0;">
                            Your OTP code for <strong>{purpose}</strong> is:
                        </p>
                        
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="background-color: #f0f0f0; padding: 25px; text-align: center; border-radius: 8px;">
                                    <h2 style="color: #667eea; font-size: 40px; letter-spacing: 10px; margin: 0; font-weight: bold; font-family: 'Courier New', monospace;">
                                        {otp}
                                    </h2>
                                </td>
                            </tr>
                        </table>
                        
                        <p style="font-size: 14px; color: #666; margin: 20px 0 10px 0;">
                            ⏰ This code will expire in <strong>10 minutes</strong>.
                        </p>
                        <p style="font-size: 14px; color: #666; margin: 0;">
                            🔒 If you didn't request this code, please ignore this email.
                        </p>
                    </td>
                </tr>
                <tr>
                    <td style="background-color: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
                        <p style="font-size: 12px; color: #999; margin: 0;">
                            This is an automated message from Minimall Store, please do not reply.
                        </p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        result = self.send_email(
            to_email=email,
            to_name=name,
            subject=f"Your Minimall OTP Code - {otp}",
            html_content=html_content
        )
        
        if result['success']:
            logger.info(f"✅ OTP email successfully sent to {email}")
        else:
            logger.error(f"❌ Failed to send OTP email to {email}")
            logger.error(f"❌ Error: {result.get('error')}")
        
        return result
    
    def send_welcome_email(self, email: str, name: str):
        """Send welcome email after successful registration"""
        logger.info(f"🎉 Preparing welcome email for {email}")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden;">
                <tr>
                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">🎉 Welcome to Minimall!</h1>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 40px 30px;">
                        <p style="font-size: 16px; color: #333; margin: 0 0 20px 0;">Hi {name},</p>
                        <p style="font-size: 14px; color: #666; margin: 0 0 20px 0;">
                            Thank you for joining <strong>Minimall</strong>! 🛍️
                        </p>
                        <p style="font-size: 14px; color: #666; margin: 0 0 30px 0;">
                            Your account has been successfully verified and you can now start shopping.
                        </p>
                        
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="text-align: center;">
                                    <a href="https://yourstore.com" 
                                       style="display: inline-block; background-color: #667eea; color: white; 
                                              padding: 14px 35px; text-decoration: none; border-radius: 5px; 
                                              font-size: 14px; font-weight: bold;">
                                        🛒 Start Shopping Now
                                    </a>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td style="background-color: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
                        <p style="font-size: 12px; color: #999; margin: 0 0 10px 0;">
                            Need help? Contact us at support@minimall.com
                        </p>
                        <p style="font-size: 12px; color: #999; margin: 0;">
                            © 2025 Minimall Store. All rights reserved.
                        </p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        result = self.send_email(
            to_email=email,
            to_name=name,
            subject="🎉 Welcome to Minimall Store!",
            html_content=html_content
        )
        
        return result
    
    def test_connection(self):
        """Test Brevo API connection and get account info"""
        try:
            logger.info("🔍 Testing Brevo API connection...")
            
            account_api = sib_api_v3_sdk.AccountApi(
                sib_api_v3_sdk.ApiClient(self.api_instance.api_client.configuration)
            )
            account = account_api.get_account()
            
            logger.info(f"✅ =================================")
            logger.info(f"✅ BREVO CONNECTION SUCCESSFUL!")
            logger.info(f"✅ Account: {account.email}")
            logger.info(f"✅ Company: {account.company_name}")
            logger.info(f"✅ Sender: {self.sender_email}")
            logger.info(f"✅ =================================")
            
            return {
                "success": True,
                "account_email": account.email,
                "company_name": account.company_name,
                "sender_email": self.sender_email,
                "sender_name": self.sender_name,
                "message": "Brevo API connection successful"
            }
        except ApiException as e:
            logger.error(f"❌ =================================")
            logger.error(f"❌ BREVO CONNECTION FAILED!")
            logger.error(f"❌ Status: {e.status}")
            logger.error(f"❌ Error: {e}")
            logger.error(f"❌ =================================")
            return {
                "success": False,
                "error": str(e),
                "status": e.status
            }

# Create singleton instance
brevo_service = BrevoEmailService()