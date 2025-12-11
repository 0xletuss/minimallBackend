from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router
from routes.product_routes import router as product_router  # Add this
from dotenv import load_dotenv 
from routes.cart_routes import router as cart_router
import os

load_dotenv()

app = FastAPI(
    title="Railway E-commerce API",
    description="FastAPI backend for e-commerce platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(product_router, prefix="/api", tags=["Products"])  # Add this
app.include_router(cart_router, prefix="/api/cart", tags=["cart"])

@app.get("/")
async def root():
    return {"message": "Railway E-commerce API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)