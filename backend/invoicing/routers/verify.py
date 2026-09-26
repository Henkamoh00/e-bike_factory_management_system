"""
invoicing/routers/verify.py

اندبوينت عام (بلا أي تسجيل دخول) لعرض صفحة تحقق من صحة فاتورة مطبوعة،
عبر مسح رمز QR الموجود على نسخة الفاتورة PDF. مسار هذا الراوتر عشوائي
المظهر وغير مرتبط بأي شكل بمسارات /api/ الخاصة بالتطبيق (راجع
verification.VERIFY_PATH_PREFIX) — تحديدًا لمنع أي عميل أو طرف خارجي من
"اكتشاف" التطبيق نفسه عبر تخمين الروابط. فقط من يملك رابط QR الدقيق
(المطبوع فعليًا على فاتورة حقيقية) يصل لهذه الصفحة.

⚠️ مستثنى من CSRFProtectionMiddleware (GET فقط، آمن أصلاً) ومن أي فحص
صلاحيات (عام بالتصميم) — آلية الحماية هنا هي توقيع HMAC وليس تسجيل الدخول.
مُستثنى أيضًا من ظهوره في /docs (include_in_schema=False).
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.rate_limit import limiter
from app.time_utils import format_local
from .. import invoices_crud
from ..verification import resolve_invoice_from_token, VERIFY_PATH_PREFIX

router = APIRouter(prefix=VERIFY_PATH_PREFIX, include_in_schema=False)


STATUS_LABELS_AR = {
    "confirmed": "مؤكدة",
    "partially_paid": "مدفوعة جزئيًا",
    "paid": "مدفوعة بالكامل",
    "cancelled": "ملغاة",
}
STATUS_COLORS = {
    "confirmed": "#2563eb",
    "partially_paid": "#d97706",
    "paid": "#059669",
    "cancelled": "#6b7280",
}


def _money(value) -> str:
    if value is None:
        value = Decimal("0")
    return f"{Decimal(value):,.2f}"


def _page_shell(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<title>التحقق من صحة الفاتورة</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 45%, #ecfdf5 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    width: 100%;
    max-width: 560px;
    background: #ffffff;
    border-radius: 28px;
    box-shadow: 0 20px 50px -12px rgba(15, 23, 42, 0.18);
    overflow: hidden;
  }}
  .header {{
    padding: 32px 32px 24px;
    text-align: center;
    border-bottom: 1px solid #f1f5f9;
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 18px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 14px;
  }}
  .body {{ padding: 28px 32px 32px; }}
  .row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f8fafc;
    font-size: 15px;
  }}
  .row:last-child {{ border-bottom: none; }}
  .row .label {{ color: #64748b; }}
  .row .value {{ color: #0f172a; font-weight: 700; }}
  .items {{ margin-top: 20px; }}
  .items h3 {{ font-size: 14px; color: #64748b; margin: 0 0 10px; }}
  .item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8fafc;
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 14px;
  }}
  .item.returned {{ background: #fff7ed; }}
  .item .chassis {{ font-family: monospace; font-weight: 700; color: #0f172a; }}
  .item .returned-tag {{
    font-size: 11px;
    background: #ffedd5;
    color: #c2410c;
    padding: 2px 8px;
    border-radius: 999px;
    margin-right: 6px;
  }}
  .totals {{
    margin-top: 20px;
    background: #f0fdf4;
    border-radius: 16px;
    padding: 16px 20px;
  }}
  .footer {{
    text-align: center;
    padding: 18px 32px 28px;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.8;
  }}
  .icon-circle {{
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 14px;
    font-size: 30px;
  }}
</style>
</head>
<body>
  <div class="card">
    {body}
  </div>
</body>
</html>"""


def _not_found_page() -> str:
    body = """
    <div class="header">
      <div class="icon-circle" style="background:#fef2f2;">⚠️</div>
      <h1 style="margin:0 0 6px; font-size:22px; color:#0f172a;">تعذّر التحقق من هذه الفاتورة</h1>
      <span class="badge" style="background:#fef2f2; color:#dc2626;">رابط غير صالح أو منتهي</span>
    </div>
    <div class="body">
      <p style="color:#64748b; font-size:14px; line-height:1.9; text-align:center; margin:0;">
        لم نتمكن من العثور على فاتورة مطابقة لهذا الرمز في سجلاتنا، أو أن
        بيانات الفاتورة الأصلية تغيّرت بما يجعل هذا الرمز غير موثوق.
        <br /><br />
        إن كنت تحمل نسخة ورقية أو PDF من هذه الفاتورة، يُرجى عدم الاعتماد
        عليها والتواصل مباشرة مع الجهة التي أصدرتها للتأكد.
      </p>
    </div>
    <div class="footer">نظام التحقق الآلي من الفواتير</div>
    """
    return _page_shell(body)


def _invoice_page(invoice) -> str:
    status_label = STATUS_LABELS_AR.get(invoice.status, invoice.status)
    status_color = STATUS_COLORS.get(invoice.status, "#334155")
    is_cancelled = invoice.status == "cancelled"

    items_html = ""
    for item in invoice.items:
        returned = getattr(item, "is_returned", False)
        tag = '<span class="returned-tag">مُرجَع</span>' if returned else ""
        items_html += f"""
        <div class="item {'returned' if returned else ''}">
          <span class="chassis">{item.chassis_number} {tag}</span>
          <span>{_money(item.unit_price)}</span>
        </div>"""

    cancel_note = ""
    if is_cancelled:
        reason = invoice.cancel_reason or "غير محدد"
        cancel_note = f"""
        <div class="row">
          <span class="label">سبب الإلغاء</span>
          <span class="value" style="color:#dc2626;">{reason}</span>
        </div>"""

    body = f"""
    <div class="header">
      <div class="icon-circle" style="background:#ecfdf5;">✅</div>
      <h1 style="margin:0 0 10px; font-size:22px; color:#0f172a;">فاتورة موثّقة وصحيحة</h1>
      <span class="badge" style="background:{status_color}1a; color:{status_color};">{status_label}</span>
    </div>
    <div class="body">
      <div class="row">
        <span class="label">رقم الفاتورة</span>
        <span class="value" style="font-family:monospace;">{invoice.invoice_number}</span>
      </div>
      <div class="row">
        <span class="label">العميل</span>
        <span class="value">{invoice.customer_name or 'غير معروف'}</span>
      </div>
      <div class="row">
        <span class="label">تاريخ الإصدار</span>
        <span class="value">{format_local(invoice.invoice_date)}</span>
      </div>
      {cancel_note}

      <div class="items">
        <h3>الدراجات ضمن هذه الفاتورة ({len(invoice.items)})</h3>
        {items_html or '<p style="color:#94a3b8; font-size:13px;">لا توجد بنود</p>'}
      </div>

      <div class="totals">
        <div class="row" style="border:none; padding:6px 0;">
          <span class="label">المجموع الفرعي</span>
          <span class="value">{_money(invoice.subtotal)}</span>
        </div>
        <div class="row" style="border:none; padding:6px 0;">
          <span class="label">الإجمالي</span>
          <span class="value">{_money(invoice.total_amount)}</span>
        </div>
        <div class="row" style="border:none; padding:6px 0;">
          <span class="label">المدفوع</span>
          <span class="value" style="color:#059669;">{_money(invoice.paid_amount)}</span>
        </div>
        <div class="row" style="border:none; padding:6px 0;">
          <span class="label">المتبقي</span>
          <span class="value" style="color:{
            '#dc2626' if Decimal(invoice.remaining_amount or 0) > 0 else '#0f172a'
          };">{_money(invoice.remaining_amount)}</span>
        </div>
      </div>
    </div>
    <div class="footer">
      هذه الصفحة تُبنى مباشرة من بيانات السيرفر الفعلية وقت الفحص، وليست من
      الملف الذي بحوزتك — أي تعديل يدوي على نسخة مطبوعة لن يظهر هنا.
      <br />نظام التحقق الآلي من الفواتير
    </div>
    """
    return _page_shell(body)


@router.get("/{token}", response_class=HTMLResponse)
@limiter.limit("30/minute")
def verify_invoice(token: str, request: Request, db: Session = Depends(get_db)):
    invoice = resolve_invoice_from_token(db, token)
    if not invoice:
        return HTMLResponse(content=_not_found_page(), status_code=404)

    invoice = invoices_crud._attach_invoice_extras(db, [invoice])[0]
    return HTMLResponse(content=_invoice_page(invoice))
