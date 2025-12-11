from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router
from routes.product_routes import router as product_router
from routes.cart_routes import router as cart_router
from routes.checkout_routes import router as checkout_router
from dotenv import load_dotenv 
import os

load_dotenv()

app = FastAPI(
    title="Railway E-commerce API",
    description="FastAPI backend for e-commerce platform",
    version="1.0.0"
)

# CORS Configuration - Allow all origins for development
# In production, replace "*" with specific frontend URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production: ["https://yourdomain.com", "http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
# Note: checkout_router already has prefix="/api/checkout" in checkout_routes.py
app.include_router(auth_router)
app.include_router(product_router)
app.include_router(cart_router)
app.include_router(checkout_router)

@app.get("/")
async def root():
    return {
        "message": "Railway E-commerce API", 
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected"  # You can add actual DB health check here
    }

# Add a test endpoint to verify CORS is working
@app.get("/api/test-cors")
async def test_cors():
    return {
        "message": "CORS is working!",
        "timestamp": "2024-12-11"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # Use reload=True for development, False for production
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)