"""
invoicing/verification.py

آلية توثيق الفواتير لمنع الاحتيال والتزوير أمام طرف ثالث (بنك، جهة
رسمية، عميل آخر...). الفكرة:

- كل فاتورة تُطبع لها رمز QR يحتوي رابطًا لصفحة تحقق عامة (بلا تسجيل دخول)
  تعرض بيانات الفاتورة المختصرة كما هي في قاعدة البيانات فعليًا وقت الفحص.
- الرابط يحمل "توكن" مبني من: معرّف الفاتورة + توقيع HMAC-SHA256 محسوب من
  بيانات الفاتورة الجوهرية (الرقم، المبلغ الإجمالي، الحالة، التاريخ) باستخدام
  مفتاح سرّي لا يظهر أبدًا كنص على المستند (لا هاش مطبوع، فقط رمز QR).
- أي تعديل يدوي على نسخة مطبوعة/PDF (مثل تغيير مبلغ بالفوتوشوب) لا يُغيّر
  بيانات قاعدة البيانات الفعلية، فصفحة التحقق ستعرض دومًا الحقيقة المخزّنة —
  هذا هو جوهر الحماية: التحقق يعتمد على السيرفر لا على الملف نفسه.
- توقيع HMAC يمنع أيضًا أي طرف من توليد توكن صالح لفاتورة وهمية أو معدَّلة
  بدون معرفة المفتاح السرّي.
"""

import os
import hmac
import hashlib
import base64
from sqlalchemy.orm import Session
from . import models


# مفتاح سرّي مستقل تمامًا عن JWT_SECRET_KEY (فصل الاستخدامات الأمنية عن
# بعضها — تسريب أحدهما لا يجب أن يُسقط الآخر معه). إجباري بلا قيمة افتراضية.
VERIFICATION_SECRET_KEY = os.getenv("INVOICE_VERIFICATION_SECRET_KEY")
if not VERIFICATION_SECRET_KEY:
    raise RuntimeError(
        "❌ متغير البيئة INVOICE_VERIFICATION_SECRET_KEY غير مُعرَّف. "
        "يجب تعيين قيمة عشوائية قوية وسرية لهذا المتغير قبل تشغيل السيرفر "
        "(مثال للتوليد: python -c \"import secrets; print(secrets.token_hex(32))\"). "
        "هذا المفتاح مستقل تمامًا عن JWT_SECRET_KEY ويُستخدم فقط لتوقيع "
        "روابط التحقق من صحة الفواتير المطبوعة."
    )

# الدومين العام الذي تُبنى عليه روابط QR — يجب أن يكون رابط السيرفر
# الفعلي المتاح للجمهور (وليس localhost)، بدون شرطة مائلة / في النهاية.
VERIFY_BASE_URL = os.getenv("INVOICE_VERIFY_BASE_URL")
if not VERIFY_BASE_URL:
    raise RuntimeError(
        "❌ متغير البيئة INVOICE_VERIFY_BASE_URL غير مُعرَّف. "
        "يجب تعيين رابط السيرفر العام الذي سيُستخدم داخل رمز QR على الفواتير "
        "(مثال: https://api.yourdomain.com)."
    )
VERIFY_BASE_URL = VERIFY_BASE_URL.rstrip("/")

# مسار عشوائي المظهر، غير مرتبط بأي شكل بمسارات التطبيق (/api/...)
# ولا يحمل أي دلالة واضحة (لا "/invoices/" ولا "/verify/") حتى لا يُستدرَج
# أي زائر لتصفح التطبيق نفسه بالخطأ. قابل للتخصيص من البيئة.
VERIFY_PATH_PREFIX = os.getenv("INVOICE_VERIFY_PATH_PREFIX", "/dq7f-doc-chk-2x9k")
if not VERIFY_PATH_PREFIX.startswith("/"):
    VERIFY_PATH_PREFIX = "/" + VERIFY_PATH_PREFIX


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def _canonical_payload(invoice: models.Invoice) -> bytes:
    """
    البيانات الجوهرية التي يغطيها التوقيع. التوقيع يُعاد حسابه من القيم
    الحالية في قاعدة البيانات وقت كل فحص (وليس وقت الطباعة)، لذا أي تعديل
    لاحق مشروع (تعديل سعر، إلغاء الفاتورة...) ينعكس تلقائيًا في صفحة التحقق.
    """
    parts = [
        str(invoice.id),
        invoice.invoice_number,
        str(invoice.total_amount),
        invoice.status,
        invoice.invoice_date.strftime("%Y-%m-%dT%H:%M:%S"),
    ]
    return "|".join(parts).encode("utf-8")


def generate_verification_token(invoice: models.Invoice) -> str:
    """يُستدعى عند توليد PDF الفاتورة لبناء رابط QR"""
    signature = hmac.new(
        VERIFICATION_SECRET_KEY.encode("utf-8"),
        _canonical_payload(invoice),
        hashlib.sha256,
    ).digest()
    id_part = _b64url_encode(str(invoice.id).encode("utf-8"))
    sig_part = _b64url_encode(signature)
    return f"{id_part}.{sig_part}"


def build_verification_url(invoice: models.Invoice) -> str:
    token = generate_verification_token(invoice)
    return f"{VERIFY_BASE_URL}{VERIFY_PATH_PREFIX}/{token}"


def resolve_invoice_from_token(db: Session, token: str) -> models.Invoice | None:
    """
    يُستدعى من الاندبوينت العام عند مسح رمز QR. يُعيد الفاتورة فقط إذا كان
    التوقيع صحيحًا ومطابقًا تمامًا للبيانات الحالية في قاعدة البيانات، وإلا
    يُعيد None بدون أي تفاصيل عن سبب الفشل (لا نُسرّب معلومات عن آلية التحقق).
    """
    try:
        id_part, sig_part = token.split(".", 1)
        invoice_id = int(_b64url_decode(id_part).decode("utf-8"))
        provided_signature = _b64url_decode(sig_part)
    except (ValueError, UnicodeDecodeError, IndexError):
        return None

    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted.is_(False))
        .first()
    )
    if not invoice:
        return None

    expected_signature = hmac.new(
        VERIFICATION_SECRET_KEY.encode("utf-8"),
        _canonical_payload(invoice),
        hashlib.sha256,
    ).digest()

    # مقارنة بزمن ثابت لمنع هجمات timing attack على التوقيع
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None

    return invoice
