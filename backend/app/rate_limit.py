import os
import warnings
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


REDIS_URL = os.getenv("REDIS_URL")

# 🛡️ مهلة زمنية صارمة (بالثواني) لأي محاولة اتصال أو عملية على Redis.
# بدونها، أي عطل شبكي صامت (جدار ناري يُسقط الحزم دون رفض) يُعلّق الطلب
# إلى الأبد بلا أي خطأ ظاهر — وهذا بالضبط ما يسبب "جاري التحميل" اللانهائي.
REDIS_CONNECT_TIMEOUT = 3   # ثواني لمحاولة فتح الاتصال
REDIS_SOCKET_TIMEOUT = 3    # ثواني لكل عملية قراءة/كتابة بعد الاتصال


def _build_redis_storage_uri(base_url: str) -> str:
    """
    يضيف مهلات timeout لرابط Redis عبر query params التي تدعمها
    مكتبة redis-py (ومن ورائها limits/slowapi).
    """
    separator = "&" if "?" in base_url else "?"
    return (
        f"{base_url}{separator}"
        f"socket_connect_timeout={REDIS_CONNECT_TIMEOUT}"
        f"&socket_timeout={REDIS_SOCKET_TIMEOUT}"
    )


def _test_redis_connection(url: str) -> bool:
    """
    اختبار فعلي وسريع للاتصال بـ Redis عند إقلاع السيرفر، بدل انتظار
    اكتشاف العطل لاحقًا أثناء تعامل مستخدم حقيقي مع الموقع (تسجيل دخول مثلاً).
    """
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
    # ── وضع الإنتاج: تخزين موزّع عبر Redis (تم التحقق من الاتصال فعليًا) ──
    limiter = Limiter(
        key_func=get_client_ip,
        storage_uri=_build_redis_storage_uri(REDIS_URL),
        default_limits=["200/minute"],
    )
    print("✅ Rate Limiting متصل بـ Redis بنجاح")
else:
    # ── تراجع آمن: تخزين بالذاكرة المحلية ────────────────────────────
    # يحدث هذا إما لعدم ضبط REDIS_URL، أو لفشل الاتصال الفعلي به
    # (شبكة/جدار ناري محلي يحجب المنفذ 6379 مثلاً)
    if REDIS_URL:
        warnings.warn(
            "⚠️ REDIS_URL مضبوط لكن الاتصال به فشل — تم التراجع تلقائيًا "
            "للتخزين بالذاكرة المحلية حتى لا يتعطل الموقع بالكامل. "
            "راجع الشبكة/الجدار الناري أو استخدم شبكة إنترنت مختلفة للاختبار."
        )
    else:
        warnings.warn(
            "⚠️ REDIS_URL غير مُعرَّف — يعمل Rate Limiting بالذاكرة المحلية فقط "
            "(غير موثوق مع أكثر من عملية/سيرفر). يجب ضبط REDIS_URL قبل النشر للإنتاج."
        )
    limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"])
