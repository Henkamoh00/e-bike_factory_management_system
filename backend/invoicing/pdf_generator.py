"""
invoicing/pdf_generator.py

🆕 توليد PDF لفاتورة واحدة (نظام الفوترة). ميزة عرض بحتة، لا تُعدّل أي
بيانات — تقرأ فقط من كائن Invoice (بعد _attach_invoice_extras) وتُنتج
ملف PDF بايتات جاهزة للإرجاع مباشرة في الاستجابة.

🆕🛡️ تتضمن الآن رمز QR للتحقق من صحة الفاتورة (راجع invoicing/verification.py):
الرمز يحتوي رابطًا لصفحة تحقق عامة على مسار منفصل تمامًا عن التطبيق، ولا
يُطبع أي هاش أو توكن كنص ظاهر على الفاتورة إطلاقًا — فقط رمز QR.

🛡️ ملاحظة تقنية حاسمة (عربي + RTL):
reportlab لا يدعم تشكيل الحروف العربية (Arabic shaping) ولا ترتيب النص
من اليمين لليسار (bidi) بشكل أصلي. لذلك كل نص عربي يُمرَّر أولاً عبر:
  1) arabic_reshaper.reshape(text)  → يُشكّل الحروف (يربط الحروف ببعضها
     بدل عرضها منفصلة كما تُكتب في يونيكود الخام)
  2) bidi.algorithm.get_display(text) → يُعيد ترتيب النص المُشكَّل ليُرسم
     بصريًا من اليمين لليسار بشكل صحيح
الأرقام والنصوص الإنجليزية (رقم الفاتورة، المبالغ) لا تحتاج هذه المعالجة
وتُرسم كما هي.

الخط: يجب توفير ملف خط TTF يدعم العربية على المسارين أدناه (راجع الشرح
المرفق مع هذا الملف). بدون خط عربي حقيقي سيرسم reportlab مربعات فارغة
(tofu) بدل الحروف.
"""

import io
import os
from decimal import Decimal
from datetime import datetime

import arabic_reshaper
from bidi.algorithm import get_display
import qrcode

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from . import models
from .verification import build_verification_url


# ====================== إعداد الخط العربي ======================
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
FONT_REGULAR_PATH = os.path.join(_ASSETS_DIR, "Arabic-Regular.ttf")
FONT_BOLD_PATH = os.path.join(_ASSETS_DIR, "Arabic-Bold.ttf")

FONT_NAME = "ArabicFont"
FONT_NAME_BOLD = "ArabicFont-Bold"

_fonts_registered = False


def _ensure_fonts_registered():
    """
    🛡️ تسجيل الخط مرة واحدة فقط لكل عملية تشغيل (تسجيل نفس اسم الخط مرتين
    يرمي خطأ من reportlab). لو ملف الخط غير موجود، نرمي خطأ عربي واضح بدل
    فشل غامض لاحقًا أثناء الرسم.
    """
    global _fonts_registered
    if _fonts_registered:
        return

    if not os.path.exists(FONT_REGULAR_PATH) or not os.path.exists(FONT_BOLD_PATH):
        raise RuntimeError(
            "❌ ملفات الخط العربي غير موجودة. يجب وضع خط TTF يدعم العربية "
            f"على المسارين: {FONT_REGULAR_PATH} و {FONT_BOLD_PATH} "
            "(مثال: Noto Naskh Arabic من Google Fonts)."
        )

    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_REGULAR_PATH))
    pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, FONT_BOLD_PATH))
    _fonts_registered = True


def _ar(text) -> str:
    """
    🆕 يُحضّر أي نص عربي (أو مختلط) للرسم الصحيح في reportlab:
    reshape ثم bidi. يتعامل بأمان مع None وبالأرقام (يُحوّلها لنص أولاً).
    """
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _money(value) -> str:
    """تنسيق المبالغ المالية بفاصلتين عشريتين دائمًا، بلا تشكيل عربي (أرقام لاتينية)"""
    if value is None:
        value = Decimal("0")
    return f"{Decimal(value):,.2f}"


def _generate_qr_image_reader(url: str) -> ImageReader:
    """
    🆕🛡️ يُنشئ رمز QR يحمل رابط صفحة التحقق فقط (لا يظهر أي هاش أو توكن
    كنص مقروء على الفاتورة نفسها — التوكن موجود فقط داخل الرابط المُشفَّر
    ضمن الرمز).
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ====================== حالة الفاتورة بالعربية ======================
STATUS_LABELS_AR = {
    "confirmed": "مؤكدة",
    "partially_paid": "مدفوعة جزئيًا",
    "paid": "مدفوعة بالكامل",
    "cancelled": "ملغاة",
}


class _InvoicePDFCanvas:
    """
    🆕 غلاف بسيط حول reportlab.canvas.Canvas لتسهيل رسم الفاتورة سطرًا بسطر
    مع دعم عربي RTL، وإدارة تلقائية للانتقال لصفحة جديدة عند امتلاء الصفحة
    الحالية (مهم للفواتير ذات عدد بنود كبير).
    """

    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 18 * mm
    RIGHT_X = PAGE_WIDTH - MARGIN  # 🆕 نبدأ الرسم من أقصى اليمين (RTL)
    LEFT_X = MARGIN

    def __init__(self, buffer):
        self.c = canvas.Canvas(buffer, pagesize=A4)
        self.y = self.PAGE_HEIGHT - self.MARGIN

    def _new_page_if_needed(self, needed_height: float):
        if self.y - needed_height < self.MARGIN + 15 * mm:
            self.c.showPage()
            self.y = self.PAGE_HEIGHT - self.MARGIN

    def draw_right_text(self, text, font=FONT_NAME, size=10, color=colors.black, dy=6 * mm):
        self._new_page_if_needed(dy)
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawRightString(self.RIGHT_X, self.y, _ar(text))
        self.y -= dy

    def draw_right_raw(self, text, font=FONT_NAME, size=10, color=colors.black, dy=6 * mm):
        """رسم نص جاهز مسبقًا (بلا إعادة تشكيل) — يُستخدم للأرقام/الإنجليزية"""
        self._new_page_if_needed(dy)
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawRightString(self.RIGHT_X, self.y, text)
        self.y -= dy

    def draw_line(self, color=colors.HexColor("#cccccc"), dy=4 * mm):
        self._new_page_if_needed(dy)
        self.c.setStrokeColor(color)
        self.c.line(self.LEFT_X, self.y, self.RIGHT_X, self.y)
        self.y -= dy

    def spacer(self, dy=4 * mm):
        self._new_page_if_needed(dy)
        self.y -= dy

    def draw_row(self, cells: list[tuple[str, float, str]], font=FONT_NAME, size=9,
                 color=colors.black, dy=6 * mm, bold=False):
        """
        🆕 يرسم صفًا بعدة أعمدة من اليمين لليسار.
        cells: قائمة (نص, عرض_العمود_بالملم, محاذاة) حيث محاذاة ∈ {"right", "left", "center"}
        """
        self._new_page_if_needed(dy)
        actual_font = FONT_NAME_BOLD if bold else font
        self.c.setFont(actual_font, size)
        self.c.setFillColor(color)

        cursor_x = self.RIGHT_X
        for text, width_mm, align in cells:
            width = width_mm * mm
            display_text = _ar(text)
            if align == "right":
                self.c.drawRightString(cursor_x, self.y, display_text)
            elif align == "left":
                self.c.drawString(cursor_x - width, self.y, display_text)
            else:
                self.c.drawCentredString(cursor_x - width / 2, self.y, display_text)
            cursor_x -= width
        self.y -= dy

    def draw_qr_block(self, image_reader: ImageReader, caption: str, qr_size_mm: float = 26):
        """
        🆕🛡️ يرسم رمز QR في الجهة اليسرى (بعيدًا عن نصوص RTL) مع تعليق
        تحته، ويحجز المساحة اللازمة عبر نظام الـ y الموحّد حتى لا يتداخل
        مع أي محتوى لاحق أو سابق.
        """
        qr_size = qr_size_mm * mm
        needed = qr_size + 8 * mm
        self._new_page_if_needed(needed)

        top_y = self.y
        self.c.drawImage(
            image_reader,
            self.LEFT_X,
            top_y - qr_size,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.c.setFont(FONT_NAME, 7)
        self.c.setFillColor(colors.HexColor("#6b7280"))
        self.c.drawCentredString(
            self.LEFT_X + qr_size / 2,
            top_y - qr_size - 4 * mm,
            _ar(caption),
        )
        self.y = top_y - needed

    def save(self):
        self.c.showPage()
        self.c.save()


def generate_invoice_pdf(invoice: models.Invoice) -> bytes:
    """
    🆕 الدالة الرئيسية: تستقبل كائن Invoice كاملًا (بعد المرور على
    invoices_crud._attach_invoice_extras — أي بعد تعبئة customer_name،
    created_by_username، is_returned لكل بند، إلخ) وتُعيد بايتات PDF جاهزة.

    🆕🛡️ تُضيف الآن رمز QR للتحقق من صحة الفاتورة (بلا أي هاش ظاهر كنص).
    """
    _ensure_fonts_registered()

    buffer = io.BytesIO()
    pdf = _InvoicePDFCanvas(buffer)

    # ====================== الترويسة ======================
    pdf.draw_right_text(
        "SAEA E-Bike Factory",
        font=FONT_NAME_BOLD, size=14, dy=8 * mm,
    )
    pdf.draw_right_text("فاتورة مبيعات", font=FONT_NAME_BOLD, size=12, dy=8 * mm)
    pdf.draw_line(dy=6 * mm)

    # ====================== بيانات الفاتورة الأساسية ======================
    pdf.draw_row(
        [(f"رقم الفاتورة: {invoice.invoice_number}", 90, "right"),
         (f"التاريخ: {invoice.invoice_date.strftime('%Y-%m-%d')}", 90, "left")],
        size=10, dy=7 * mm,
    )
    pdf.draw_row(
        [(f"العميل: {invoice.customer_name or 'غير معروف'}", 90, "right"),
         (f"الحالة: {STATUS_LABELS_AR.get(invoice.status, invoice.status)}", 90, "left")],
        size=10, dy=7 * mm,
    )
    if getattr(invoice, "created_by_username", None):
        pdf.draw_right_text(f"أُنشئت بواسطة: {invoice.created_by_username}", size=9, dy=6 * mm)

    if invoice.status == "cancelled":
        pdf.draw_right_text(
            f"⚠️ فاتورة ملغاة" + (f" — السبب: {invoice.cancel_reason}" if invoice.cancel_reason else ""),
            font=FONT_NAME_BOLD, size=10, color=colors.HexColor("#b91c1c"), dy=7 * mm,
        )

    # ====================== 🆕 رمز التحقق (QR) ======================
    try:
        verify_url = build_verification_url(invoice)
        qr_reader = _generate_qr_image_reader(verify_url)
        pdf.draw_qr_block(qr_reader, "امسح للتحقق من صحة الفاتورة")
    except RuntimeError:
        # 🛡️ لو لم تُعرَّف متغيرات بيئة التحقق (INVOICE_VERIFICATION_SECRET_KEY
        # أو INVOICE_VERIFY_BASE_URL)، لا نُفشل توليد الفاتورة بالكامل بسبب
        # ميزة إضافية — نتجاهل QR فقط ونكمل بقية المستند
        pass

    pdf.spacer(dy=3 * mm)

    # ====================== جدول البنود ======================
    pdf.draw_line(dy=1 * mm)
    pdf.spacer(dy=4 * mm)
    pdf.draw_row(
        [("رقم الهيكل", 45, "right"),
         ("السعر", 30, "center"),
         ("الحالة", 30, "center"),
         ("ملاحظات", 65, "right")],
        bold=True, size=10, dy=7 * mm,
    )
    pdf.draw_line(dy=4 * mm)

    for item in invoice.items:
        item_status = "مُرجَع" if getattr(item, "is_returned", False) else "نشط"
        pdf.draw_row(
            [(item.chassis_number, 45, "right"),
             (_money(item.unit_price), 30, "center"),
             (item_status, 30, "center"),
             (item.notes or "-", 65, "right")],
            size=9, dy=6 * mm,
        )
        if getattr(item, "is_returned", False) and item.return_reason:
            pdf.draw_right_text(f"   سبب الإرجاع: {item.return_reason}", size=8,
                                 color=colors.HexColor("#6b7280"), dy=5 * mm)

    pdf.spacer(dy=2 * mm)
    pdf.draw_line(dy=5 * mm)

    # ====================== الإجماليات ======================
    pdf.draw_row(
        [(f"المجموع الفرعي: {_money(invoice.subtotal)}", 180, "right")],
        size=10, dy=6 * mm,
    )
    if invoice.discount_value and Decimal(invoice.discount_value) > 0:
        discount_label = (
            f"الخصم ({invoice.discount_value}%):"
            if invoice.discount_type == "percentage"
            else "الخصم (مبلغ ثابت):"
        )
        pdf.draw_row(
            [(f"{discount_label} {_money(invoice.subtotal - invoice.total_amount)}", 180, "right")],
            size=10, dy=6 * mm,
        )
    pdf.draw_row(
        [(f"الإجمالي: {_money(invoice.total_amount)}", 180, "right")],
        bold=True, size=11, dy=7 * mm,
    )
    pdf.draw_row(
        [(f"المدفوع: {_money(invoice.paid_amount)}", 180, "right")],
        size=10, dy=6 * mm,
    )
    pdf.draw_row(
        [(f"المتبقي: {_money(invoice.remaining_amount)}", 180, "right")],
        bold=True, size=10,
        color=colors.HexColor("#b91c1c") if invoice.remaining_amount and Decimal(invoice.remaining_amount) > 0 else colors.black,
        dy=8 * mm,
    )

    # ====================== الدفعات ======================
    if invoice.payments:
        pdf.draw_line(dy=4 * mm)
        pdf.draw_right_text("سجل الدفعات", font=FONT_NAME_BOLD, size=11, dy=7 * mm)
        pdf.draw_row(
            [("التاريخ", 40, "right"),
             ("المبلغ", 40, "center"),
             ("الطريقة", 45, "center"),
             ("بواسطة", 45, "right")],
            bold=True, size=9, dy=6 * mm,
        )
        for p in invoice.payments:
            pdf.draw_row(
                [(p.payment_date.strftime("%Y-%m-%d"), 40, "right"),
                 (_money(p.amount), 40, "center"),
                 (p.payment_method or "-", 45, "center"),
                 (getattr(p, "recorded_by_username", None) or "-", 45, "right")],
                size=9, dy=6 * mm,
            )

    if invoice.notes:
        pdf.spacer(dy=3 * mm)
        pdf.draw_line(dy=4 * mm)
        pdf.draw_right_text(f"ملاحظات: {invoice.notes}", size=9, dy=6 * mm)

    # ====================== تذييل ======================
    pdf.spacer(dy=6 * mm)
    footer_text = f"برج الكيفان، بتاريخ {datetime.now().strftime('%d-%m-%Y')} على الساعة {datetime.now().strftime('%H:%M')}"
    pdf.draw_right_text(footer_text, size=7, color=colors.HexColor("#9ca3af"), dy=5 * mm)

    pdf.save()
    return buffer.getvalue()