from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.auth_routes import router as auth_router
from routes.product_routes import router as product_router
from routes.cart_routes import router as cart_router
from routes.checkout_routes import router as checkout_router
from routes.profile_routes import router as profile_router
from routes.seller_product_routes import router as seller_product_router
from routes.image_routes import router as image_router
from routes.order_route import router as order_router

from dotenv import load_dotenv 
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

app = FastAPI(
    title="Railway E-commerce API",
    description="FastAPI backend for e-commerce platform with multi-vendor support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(product_router, prefix="/api", tags=["Products"])
app.include_router(cart_router, prefix="/api/cart", tags=["Cart"])
app.include_router(checkout_router, prefix="/api/checkout", tags=["Checkout"])
app.include_router(checkout_router, prefix="/api", tags=["Orders"])
app.include_router(profile_router, prefix="/api", tags=["Profile"])
app.include_router(seller_product_router, prefix="/api", tags=["Seller Products"])
app.include_router(image_router, prefix="/api", tags=["Image Upload"])
app.include_router(order_router, prefix="/api", tags=["Order Management"])


@app.get("/")
async def root():
    return {
        "message": "Railway E-commerce API", 
        "status": "running",
        "version": "1.0.0",
        "features": [
            "Multi-vendor marketplace",
            "Order management",
            "Seller dashboard",
            "Customer orders",
            "Email notifications via Brevo",
            "OTP authentication"
        ]
    }

@app.get("/health")
async def health_check():
    email_status = "configured" if hasattr(app.state, 'email_api') and app.state.email_api else "not configured"
    return {
        "status": "healthy", 
        "timestamp": "2025-12-26",
        "email_service": email_status
    }

@app.post("/api/test-email")
async def test_email(email: str):
    """Test endpoint to verify Brevo is working"""
    if not hasattr(app.state, 'email_api') or app.state.email_api is None:
        return JSONResponse(
            status_code=500,
            content={"error": "Email service not configured. Check BREVO_API_KEY environment variable."}
        )
    
    try:
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email}],
            sender={"email": "noreply@yourdomain.com", "name": "Your E-commerce Store"},
            subject="Test Email from Your API",
            html_content="<html><body><h1>Success! 🎉</h1><p>Brevo email integration is working correctly.</p></body></html>"
        )
        
        response = app.state.email_api.send_transac_email(send_smtp_email)
        return {
            "success": True, 
            "message": "Email sent successfully!",
            "message_id": response.message_id,
            "to": email
        }
    except ApiException as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Brevo API Error: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    
    # Initialize Brevo Email Service
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
        app.state.email_api = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        print("✅ Brevo email service initialized")
    except Exception as e:
        print(f"⚠️ Brevo initialization failed: {e}")
        app.state.email_api = None
    
    # Create OTP table
    try:
        from models.otp_model import OTPModel
        otp_model = OTPModel()
        otp_model.create_otp_table()
        print("✅ OTP table created/verified")
    except Exception as e:
        print(f"⚠️ OTP table creation failed: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
