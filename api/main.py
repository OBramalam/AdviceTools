import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import api_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Financial Simulation API",
    description="API for financial planning and retirement simulations",
    version="1.0.0",
)

# CORS configuration - read from environment variable
frontend_url = os.getenv("FRONTEND_URL", "")
cors_origins = [
    "http://localhost:3000",  # React default port
    "http://localhost:5173",   # Vite default port
]
if frontend_url:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "message": "Financial Simulation API",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)

