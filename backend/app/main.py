from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from .routers import workers, bike_options, customers, sales, faults, chassis, assembly, stats, auth, users, roles, logs
from .rate_limit import limiter

# إنشاء الجداول عند بدء التطبيق (للتطوير)
# models.Base.metadata.create_all(bind=engine)

# 🛡️ تمت إزالة models.Base.metadata.create_all(bind=engine) نهائيًا.
# إدارة المخطط (schema) أصبحت حصريًا عبر Alembic migrations من الآن فصاعدًا:
#   - إنشاء migration جديدة:  alembic revision --autogenerate -m "وصف التغيير"
#   - تطبيقها على القاعدة:    alembic upgrade head
# الاعتماد على create_all() كان يعني عدم وجود سجل تاريخي للتغييرات، ويمنع
# التراجع (downgrade) أو تتبّع من غيّر ماذا ومتى على مستوى بنية القاعدة.

app = FastAPI(
    title="نظام إدارة تجميع الدراجات الكهربائية",
    description="نظام تتبع كامل للدراجات الكهربائية",
    version="1.0.0"
)

# ── تفعيل Rate Limiting على مستوى التطبيق بأكمله ──────────────────
app.state.limiter = limiter


# 🛡️ معالج مخصص لرسالة عربية واضحة بدل رسالة slowapi الإنجليزية الافتراضية
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = None
    if hasattr(exc, "retry_after"):
        retry_after = str(exc.retry_after)

    headers = {}
    if retry_after:
        headers["Retry-After"] = retry_after

    return JSONResponse(
        status_code=429,
        content={"detail": "⛔ عدد كبير جداً من المحاولات في وقت قصير. يرجى الانتظار قليلاً ثم إعادة المحاولة."},
        headers=headers,
    )

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# 🛡️🛡️ الترتيب حاسم هنا: SlowAPIMiddleware يجب أن يُضاف قبل CORSMiddleware
# حتى يبقى CORSMiddleware هو الطبقة الخارجية (يُنفَّذ أولاً على كل طلب/استجابة)
# ويضمن إضافة هيدرز Access-Control-* حتى على استجابات 429، وإلا يفشل
# المتصفح بصمت في preflight (OPTIONS) ويظهر الأمر كأن لا بيانات تصل إطلاقاً
app.add_middleware(SlowAPIMiddleware)

origins = [
    "https://electricbikemanager.app",
    "https://electricbikemanager.vercel.app",
    "http://localhost:5173",  # لبيئة التطوير المحلية أيضاً
    "http://127.0.0.1:5173",
]

# CORS — يجب أن يبقى آخر middleware يُضاف (= أول طبقة تنفيذ)
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
app.include_router(roles.router)
app.include_router(logs.router)


@app.get("/")
def root():
    return {
        "message": "🚀 نظام إدارة الدراجات الكهربائية يعمل بنجاح",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}