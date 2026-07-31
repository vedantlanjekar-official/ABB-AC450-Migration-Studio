from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.api import upload, process, status, download, logs

logger = get_logger()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Backend service for ABB AC450 Migration Studio: DB/PC PDF conversion, "
        "Excel tag comparison, I/O address arrangement, and engineering templates."
    ),
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
    filesystem_ok = True
    filesystem_error = None
    probe_path = settings.LOG_DIR / ".health_probe"
    try:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
    except Exception as exc:
        filesystem_ok = False
        filesystem_error = str(exc)
        logger.error(f"Health check filesystem probe failed: {exc}", exc_info=True)

    return {
        "status": "online" if filesystem_ok else "degraded",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "filesystem": {
            "writable": filesystem_ok,
            "upload_dir": str(settings.UPLOAD_DIR),
            "output_dir": str(settings.OUTPUT_DIR),
            "log_dir": str(settings.LOG_DIR),
            "error": filesystem_error,
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
