import os
import warnings
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from jose import jwt, JWTError


# 🛡️🆕 قائمة عناوين IP الخاصة بالبروكسي/Load Balancer الموثوق فقط.
# لا يُوثَق بهيدر X-Forwarded-For إلا إذا كان الطلب قادمًا فعليًا من أحد
# هذه العناوين مباشرة (أي أن request.client.host هو عنوان البروكسي نفسه).
# بدون هذا الفحص، أي مهاجم يستطيع إرسال X-Forwarded-For مزيّف مختلف مع كل
# طلب للتحايل الكامل على حد "5 محاولات/دقيقة" في تسجيل الدخول.
# اضبط هذا المتغير في بيئة الإنتاج بعناوين IP الخاصة بمزوّد الاستضافة
# (مثال: Render/Railway/Nginx reverse proxy)، مفصولة بفواصل.
_raw_trusted = os.getenv("TRUSTED_PROXY_IPS", "")
TRUSTED_PROXY_IPS = {ip.strip() for ip in _raw_trusted.split(",") if ip.strip()}

if not TRUSTED_PROXY_IPS:
    warnings.warn(
        "⚠️ TRUSTED_PROXY_IPS غير مُعرَّف — سيتم تجاهل هيدر X-Forwarded-For "
        "بالكامل والاعتماد فقط على عنوان IP المباشر للاتصال (request.client.host). "
        "إذا كان السيرفر خلف بروكسي/load balancer فعليًا، يجب ضبط هذا المتغير "
        "وإلا ستُطبَّق حدود Rate Limiting على IP البروكسي نفسه لكل المستخدمين معًا."
    )


def get_client_ip(request: Request) -> str:
    direct_ip = get_remote_address(request)

    # 🛡️ الوثوق بـ X-Forwarded-For فقط إذا كان الاتصال المباشر قادمًا من
    # بروكسي معروف ومُدرَج صراحة في القائمة الموثوقة
    if direct_ip in TRUSTED_PROXY_IPS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # أول عنوان بالسلسلة هو عنوان العميل الأصلي (المُضاف من البروكسي
            # الموثوق نفسه، وليس من العميل، طالما البروكسي مُهيَّأ بشكل صحيح)
            return forwarded.split(",")[0].strip()

    return direct_ip


# 🛡️🆕 مفتاح Rate Limiting معتمد على هوية المستخدم (من توكن الوصول) بدل IP.
# السبب: عدة عمال (operators) قد يعملون خلف نفس IP العام لشبكة الورشة الداخلية،
# فربط الحد بـ IP يجعلهم يتشاركون نفس السقف اليومي/الساعي بالخطأ — بينما الهدف
# الفعلي من هذه الحدود هو منع إساءة استخدام حساب واحد وليس منع نشاط الورشة كلها.
#
# 🔑 يعتمد فقط على فك تشفير التوكن (بدون أي استعلام لقاعدة البيانات) للحفاظ على
# خفة key_func كما يتطلبه slowapi، ثم يُعيد "user:{username}" كمفتاح فريد لكل مستخدم.
# لو تعذّر استخراج توكن صالح (طلب غير مُصادَق، توكن منتهي/تالف)، يتم التراجع
# تلقائيًا لعنوان IP كحل بديل بدل رفض الطلب أو كسر منطق الحد بالكامل.
#
# ⚠️ ملاحظة: هذه الدالة لا تُستخدم في مسار /api/auth/login/ عمدًا؛ فالمستخدم هناك
# غير مُصادَق بعد (لا يوجد توكن صالح لاستخراج هويته منه)، والمهاجم هو من يتحكم
# بحقل username المُرسَل، فلا يمكن الوثوق به كمفتاح — الحماية من Brute Force
# يجب أن تبقى مرتبطة بمصدر الاتصال الفعلي (IP) في ذلك المسار تحديدًا.
def get_rate_limit_key(request: Request) -> str:
    from .security import ACCESS_COOKIE_NAME, SECRET_KEY, ALGORITHM

    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username and payload.get("type") == "access":
                return f"user:{username}"
        except JWTError:
            pass

    # تراجع آمن: طلب بدون هوية صالحة يُحدَّد بعنوان IP بدل تعطيل الحد كليًا
    return f"ip:{get_client_ip(request)}"


REDIS_URL = os.getenv("REDIS_URL")

REDIS_CONNECT_TIMEOUT = 3
REDIS_SOCKET_TIMEOUT = 3


def _build_redis_storage_uri(base_url: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return (
        f"{base_url}{separator}"
        f"socket_connect_timeout={REDIS_CONNECT_TIMEOUT}"
        f"&socket_timeout={REDIS_SOCKET_TIMEOUT}"
    )


def _test_redis_connection(url: str) -> bool:
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(
            url,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
        )
        client.ping()
        client.close()
        return True
    except Exception as e:
        warnings.warn(f"⚠️ تعذر الاتصال بـ Redis عبر REDIS_URL: {e}")
        return False


if REDIS_URL and _test_redis_connection(REDIS_URL):
    limiter = Limiter(
        key_func=get_client_ip,
        storage_uri=_build_redis_storage_uri(REDIS_URL),
        default_limits=["200/minute"],
    )
    print("✅ Rate Limiting متصل بـ Redis بنجاح")
else:
    if REDIS_URL:
        warnings.warn(
            "⚠️ REDIS_URL مضبوط لكن الاتصال به فشل — تم التراجع تلقائيًا "
            "للتخزين بالذاكرة المحلية حتى لا يتعطل الموقع بالكامل."
        )
    else:
        warnings.warn(
            "⚠️ REDIS_URL غير مُعرَّف — يعمل Rate Limiting بالذاكرة المحلية فقط."
        )
    limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"])