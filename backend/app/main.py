import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist (SQLite development or first run)
    Base.metadata.create_all(bind=engine)
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "HEALORA is a smart hospital communication and clinical workflows platform "
        "connecting patients, doctors, and hospital administrators with AI-assisted triage "
        "and doctor-in-the-loop clinical decision support."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded medical records/documents safely
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Serve frontend static files (checks local backend/static or repository root ../static)
static_dir = next((d for d in ["static", "../static"] if os.path.exists(d) and os.path.isdir(d)), None)
if static_dir:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    for index_path in ["static/index.html", "../static/index.html"]:
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return RedirectResponse(url="/docs")

