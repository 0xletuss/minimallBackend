from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.auth_routes import router as auth_router
from routes.product_routes import router as product_router
from routes.cart_routes import router as cart_router
from routes.checkout_routes import router as checkout_router
from routes.profile_routes import router as profile_router  # Add this

from dotenv import load_dotenv 
import os

load_dotenv()

app = FastAPI(
    title="Railway E-commerce API",
    description="FastAPI backend for e-commerce platform",
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
app.include_router(profile_router, prefix="/api", tags=["Profile"])  # Add this

@app.get("/")
async def root():
    return {"message": "Railway E-commerce API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)