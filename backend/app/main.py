import secrets
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from .routers import workers, bike_options, customers, faults, chassis, assembly, stats, auth, users, roles, logs
from invoicing.routers.invoices import router as invoices_router
from invoicing.routers.verify import router as invoice_verify_router
from .rate_limit import limiter
from .security import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME

app = FastAPI(
    title="نظام إدارة تجميع الدراجات الكهربائية",
    description="نظام تتبع كامل للدراجات الكهربائية",
    version="1.0.0"
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


# 🛡️🆕 Middleware حماية CSRF (نمط Double Submit Cookie)
# يُنفَّذ على أي طلب غير آمن (POST/PUT/DELETE/PATCH) قادم من عميل يحمل جلسة
# كوكيز (access أو refresh). المسارات المُستثناة: تسجيل الدخول (لا جلسة بعد)
# وتسجيل الخروج (إجراء آمن نسبيًا، ولمنع قفل المستخدم في حال فقد كوكي CSRF).
# ⚠️ صفحة التحقق العامة (invoice_verify_router) لا تحتاج استثناء هنا أصلاً
# لأنها GET فقط، والـ GET مُستثنى بالفعل ضمن SAFE_METHODS.
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


# 🛡️🛡️ الترتيب حاسم: CSRFProtectionMiddleware و SlowAPIMiddleware يجب أن
# يُضافا قبل CORSMiddleware حتى يبقى CORSMiddleware الطبقة الخارجية الأولى
app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(SlowAPIMiddleware)

origins = [
    "https://electricbikemanager.app",
    "https://electricbikemanager.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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
        CSRF_HEADER_NAME,  # 🛡️🆕 يجب السماح به صراحة ليصل هيدر CSRF
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

# 🆕🛡️ راوتر التحقق العام من صحة الفواتير — مسار عشوائي بعيد تمامًا عن
# /api/، بلا تسجيل دخول، وبلا ظهور في /docs (راجع invoicing/verification.py
# و invoicing/routers/verify.py). يُستدعى فقط من مسح رمز QR على فاتورة PDF.
app.include_router(invoice_verify_router)


@app.get("/")
def root():
    return {
        "message": "🚀 نظام إدارة الدراجات الكهربائية يعمل بنجاح",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}