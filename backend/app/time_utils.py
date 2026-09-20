"""
app/time_utils.py

مصدر واحد للتعامل مع الوقت في المشروع كله (راجع قسم "قواعد ثابتة" في NOTES.md).

القاعدة الموحّدة:
- كل وقت "حالي" يُنشأ بـ utcnow() → datetime واعٍ بالمنطقة (aware) بتوقيت UTC.
- أي قيمة datetime مقروءة من قاعدة البيانات تمر عبر ensure_utc() قبل أي
  مقارنة أو طرح: PostgreSQL (timestamptz) يُرجع قيمًا aware، بينما SQLite
  (الاختبارات) يُرجع قيمًا naive — الدالة توحّد الحالتين إلى aware UTC.
  القيمة الـ naive تُعتبر دائمًا UTC (لأن كل ما نكتبه هو UTC).
- ممنوع: datetime.utcnow()، ولا .replace(tzinfo=None) على وقت غير UTC،
  ولا مقارنة aware مع naive مباشرة.

التوقيت المرجعي للعرض وحدود الفترات ("اليوم/الأسبوع/الشهر/السنة")
هو Africa/Algiers (UTC+1 طوال السنة، بلا توقيت صيفي): التخزين دائمًا UTC،
والتحويل للتوقيت المحلي يتم فقط عند العرض أو عند حساب حدود الفترات.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# 🛡️ على Windows لا توجد قاعدة بيانات مناطق زمنية في النظام (تحتاج حزمة tzdata).
# الجزائر UTC+1 ثابتة بلا توقيت صيفي، فنتراجع لإزاحة ثابتة مطابقة تمامًا
# عند غياب البيانات، بدل أن ينهار التطبيق عند الاستيراد.
try:
    APP_TZ = ZoneInfo("Africa/Algiers")
except ZoneInfoNotFoundError:
    APP_TZ = timezone(timedelta(hours=1), "Africa/Algiers")


def utcnow() -> datetime:
    """الوقت الحالي بتوقيت UTC (aware)"""
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """
    يحوّل أي datetime إلى aware UTC:
    - naive  → يُعتبر UTC أصلاً (يُضاف له tzinfo فقط دون تغيير القيمة)
    - aware  → يُحوَّل فعليًا إلى UTC (يراعي فرق التوقيت إن وُجد)
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    """
    هل انتهت الصلاحية؟ الحد الفاصل صارم: عند اللحظة نفسها (expires_at == now)
    يُعتبر منتهيًا، فالصالح فقط ما كان expires_at بعد الآن تمامًا.
    """
    current = ensure_utc(now) if now is not None else utcnow()
    return ensure_utc(expires_at) <= current


def to_local(dt: datetime | None) -> datetime | None:
    """أي datetime → aware بتوقيت الجزائر (للعرض)؛ القيمة naive تُعتبر UTC"""
    utc_dt = ensure_utc(dt)
    return utc_dt.astimezone(APP_TZ) if utc_dt is not None else None


def format_local(dt: datetime | None, fmt: str = "%Y-%m-%d") -> str:
    """تنسيق وقت بتوقيت الجزائر كنص (سلسلة فارغة لو None)"""
    local = to_local(dt)
    return local.strftime(fmt) if local is not None else ""


def local_start_of_day_utc(year: int, month: int, day: int = 1) -> datetime:
    """بداية اليوم (00:00) بتوقيت الجزائر، مُحوَّلة إلى aware UTC للمقارنة مع قيم القاعدة"""
    return datetime(year, month, day, tzinfo=APP_TZ).astimezone(timezone.utc)


def local_naive_to_utc(dt: datetime) -> datetime:
    """
    قيمة قادمة من مستخدم (مثل فلتر تاريخ): إن كانت naive تُفسَّر بتوقيت
    الجزائر (وليس UTC) ثم تُحوَّل إلى UTC؛ وإن كانت aware تُحوَّل مباشرة.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(timezone.utc)
