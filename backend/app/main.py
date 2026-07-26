from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import workers, bike_options, customers, sales, faults, chassis, assembly, stats, auth, users
from .database import engine
from . import models

# إنشاء الجداول عند بدء التطبيق (للتطوير)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="نظام إدارة تجميع الدراجات الكهربائية",
    description="نظام تتبع كامل للدراجات الكهربائية",
    version="1.0.0"
)

origins = [
    "https://electricbikemanager.app",
    "https://electricbikemanager.vercel.app",
    "http://localhost:5173",  # لبيئة التطوير المحلية أيضاً
    "http://127.0.0.1:5173",
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # غير هذا لاحقاً في الإنتاج
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "ngrok-skip-browser-warning"  # 👈 يجب كتابته صراحة هنا بالاسم!
    ],
    expose_headers=["X-Confirm-Required"],
)

# Routers
app.include_router(workers.router)
app.include_router(bike_options.router)
app.include_router(customers.router)
app.include_router(sales.router)
app.include_router(faults.router)
app.include_router(chassis.router)
app.include_router(assembly.router)
app.include_router(stats.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {
        "message": "🚀 نظام إدارة الدراجات الكهربائية يعمل بنجاح",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}