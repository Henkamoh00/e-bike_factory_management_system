from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import workshop, admin
from .database import engine
from . import models

# إنشاء الجداول عند بدء التطبيق (للتطوير)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="نظام إدارة تجميع الدراجات الكهربائية",
    description="نظام تتبع كامل للدراجات الكهربائية",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # غير هذا لاحقاً في الإنتاج
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Confirm-Required"],
)

# Routers
app.include_router(workshop.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "🚀 نظام إدارة الدراجات الكهربائية يعمل بنجاح",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}