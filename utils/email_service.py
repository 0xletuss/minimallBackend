import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
from typing import List, Optional

class BrevoEmailService:
    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
    
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        sender_email: str = "noreply@yourdomain.com",
        sender_name: str = "Your Store Name"
    ):
        """Send a transactional email via Brevo"""
        try:
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email, "name": to_name}],
                sender={"email": sender_email, "name": sender_name},
                subject=subject,
                html_content=html_content
            )
            
            response = self.api_instance.send_transac_email(send_smtp_email)
            return {"success": True, "message_id": response.message_id}
        except ApiException as e:
            print(f"Brevo API Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def send_order_confirmation(self, order_data: dict):
        """Send order confirmation email"""
        html_content = f"""
        <html>
            <body>
                <h2>Order Confirmation</h2>
                <p>Hi {order_data['customer_name']},</p>
                <p>Thank you for your order!</p>
                <p><strong>Order ID:</strong> {order_data['order_id']}</p>
                <p><strong>Total:</strong> ${order_data['total']}</p>
                <p>We'll send you shipping updates soon.</p>
            </body>
        </html>
        """
        
        return self.send_email(
            to_email=order_data['customer_email'],
            to_name=order_data['customer_name'],
            subject=f"Order Confirmation - #{order_data['order_id']}",
            html_content=html_content
        )
    
    def send_password_reset(self, email: str, name: str, reset_link: str):
        """Send password reset email"""
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hi {name},</p>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_link}">Reset Password</a>
                <p>This link will expire in 1 hour.</p>
            </body>
        </html>
        """
        
        return self.send_email(
            to_email=email,
            to_name=name,
            subject="Password Reset Request",
            html_content=html_content
        )

# Create a singleton instance
brevo_service = BrevoEmailService()