from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api import upload, process, status, download, logs

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend service for converting ABB AC450 DB Element PDFs into Valmet Excel workbooks."
)

# Enable CORS for Next.js frontend (Vercel or local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(upload.router, prefix=settings.API_PREFIX)
app.include_router(process.router, prefix=settings.API_PREFIX)
app.include_router(status.router, prefix=settings.API_PREFIX)
app.include_router(download.router, prefix=settings.API_PREFIX)
app.include_router(logs.router, prefix=settings.API_PREFIX)

@app.get("/health")
@app.get(f"{settings.API_PREFIX}/health")
async def health_check():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
