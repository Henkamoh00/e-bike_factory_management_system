import os
import asyncio
import secrets
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from .routers import workers, bike_options, customers, faults, chassis, assembly, stats, auth, users, roles, logs
from invoicing.routers.invoices import router as invoices_router
from invoicing.routers.verify import router as invoice_verify_router
from inventory.routers.inventory import router as inventory_router
from .database import SessionLocal
from . import auth_crud
from .rate_limit import limiter
from .security import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME


# ====================== تنظيف دوري لتوكنات التحديث القديمة ======================
# تعمل مرة كل 5 أيام، وتحذف كل توكن انتهت صلاحيته قبل أكثر من 30 يومًا
# (راجع auth_crud.purge_expired_refresh_tokens). أول تشغيل بعد 30 دقائق من
# إقلاع الخادم كي لا تتزاحم مع بدء التشغيل أو تتداخل مع الاختبارات.
TOKEN_CLEANUP_FIRST_DELAY_SECONDS = 30 * 60
TOKEN_CLEANUP_INTERVAL_SECONDS = 5 * 24 * 60 * 60


def _run_token_cleanup():
    db = SessionLocal()
    try:
        deleted = auth_crud.purge_expired_refresh_tokens(db)
        if deleted:
            print(f"🧹 تم حذف {deleted} توكن تحديث قديم")
    finally:
        db.close()


async def _token_cleanup_loop():
    await asyncio.sleep(TOKEN_CLEANUP_FIRST_DELAY_SECONDS)
    while True:
        try:
            await asyncio.to_thread(_run_token_cleanup)
        except Exception as e:
            # 🛡️ فشل التنظيف لا يجب أن يوقف التطبيق أو المهمة نفسها أبدًا
            print(f"⚠️ تعذر تنظيف توكنات التحديث القديمة: {e}")
        await asyncio.sleep(TOKEN_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_task = asyncio.create_task(_token_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(
    title="نظام إدارة تجميع الدراجات الكهربائية",
    description="نظام تتبع كامل للدراجات الكهربائية",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


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


# حماية CSRF (نمط Double Submit Cookie): تُطبَّق على أي طلب غير آمن من عميل
# يحمل جلسة كوكيز. مستثنى: تسجيل الدخول والخروج. الطلبات GET آمنة أصلاً.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PATHS = {
    "/api/auth/login/",
    "/api/auth/logout/",
}


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in SAFE_METHODS and request.url.path not in CSRF_EXEMPT_PATHS:
            has_cookie_session = bool(
                request.cookies.get(ACCESS_COOKIE_NAME) or request.cookies.get(REFRESH_COOKIE_NAME)
            )
            if has_cookie_session:
                csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
                csrf_header = request.headers.get(CSRF_HEADER_NAME)
                if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "⛔ فشل التحقق من CSRF token. يرجى إعادة تحميل الصفحة."},
                    )
        return await call_next(request)


# الترتيب حاسم: يجب إضافة CSRF وSlowAPI قبل CORS ليبقى CORS الطبقة الخارجية
app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(SlowAPIMiddleware)

# النطاقات المسموحة من متغير البيئة CORS_ORIGINS (مفصولة بفواصل)
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "ngrok-skip-browser-warning",
        CSRF_HEADER_NAME,
    ],
    expose_headers=["X-Confirm-Required"],
)

# Routers
app.include_router(workers.router)
app.include_router(bike_options.router)
app.include_router(customers.router)
app.include_router(faults.router)
app.include_router(chassis.router)
app.include_router(assembly.router)
app.include_router(stats.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(logs.router)
app.include_router(invoices_router)
app.include_router(invoice_verify_router)
app.include_router(inventory_router)


@app.get("/")
def root():
    return {
        "message": "🚀 نظام إدارة الدراجات الكهربائية يعمل بنجاح",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
