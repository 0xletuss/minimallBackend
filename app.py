from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

# Nuclear CORS handler - handles ALL requests
@app.middleware("http")
async def super_cors_middleware(request: Request, call_next):
    # Immediately handle ALL OPTIONS requests
    if request.method == "OPTIONS":
        return JSONResponse(
            content={"message": "OK"},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    # For all other requests, process and add CORS headers
    try:
        response = await call_next(request)
    except Exception as e:
        # Even on errors, return with CORS headers
        return JSONResponse(
            content={"detail": str(e)},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Add CORS headers to response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(product_router, prefix="/api", tags=["Products"])
app.include_router(cart_router, prefix="/api/cart", tags=["Cart"])
app.include_router(checkout_router, prefix="/api/checkout", tags=["Checkout"])

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