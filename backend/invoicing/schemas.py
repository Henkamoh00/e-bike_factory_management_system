from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from decimal import Decimal
from app.models import AssemblyStage


class StrippedBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _strip_string_fields(cls, data):
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, str):
                    cleaned[key] = value.strip()
                else:
                    cleaned[key] = value
            return cleaned
        return data


# ====================== بنود الفاتورة ======================
class InvoiceItemCreate(StrippedBaseModel):
    chassis_number: str
    unit_price: Decimal
    notes: str | None = None


class InvoiceItemUpdate(StrippedBaseModel):
    unit_price: Decimal | None = None
    notes: str | None = None


class InvoiceItemResponse(BaseModel):
    id: int
    chassis_number: str
    unit_price: Decimal
    notes: str | None = None
    is_returned: bool = False
    return_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== الدفعات ======================
class PaymentCreate(StrippedBaseModel):
    amount: Decimal = Decimal("0")
    payment_method: str | None = None
    payment_date: datetime | None = None
    notes: str | None = None
    # مبلغ يُستخدم من رصيد العميل كجزء (أو كل) هذه الدفعة، بدل الدفع
    # النقدي بالكامل. يمكن الجمع بين مبلغ نقدي + رصيد في نفس الدفعة.
    use_credit_amount: Decimal | None = None


class PaymentUpdate(StrippedBaseModel):
    amount: Decimal | None = None
    payment_method: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    payment_method: str | None = None
    payment_date: datetime
    notes: str | None = None
    recorded_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== إرجاع الدراجات المباعة ======================
class ChassisReturnCreate(StrippedBaseModel):
    invoice_item_id: int
    reason: str
    related_fault_id: int | None = None
    create_fault_stage: AssemblyStage | None = None
    notes: str | None = None


class ChassisReturnResponse(BaseModel):
    id: int
    invoice_item_id: int
    chassis_number: str
    invoice_number: str
    customer_name: str
    reason: str
    related_fault_id: int | None = None
    notes: str | None = None
    created_by_username: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedReturns(BaseModel):
    items: list[ChassisReturnResponse]
    total: int


class ReturnableChassisResponse(BaseModel):
    invoice_item_id: int
    chassis_number: str
    invoice_number: str
    customer_name: str


class SoldFaultyFaultBrief(BaseModel):
    id: int
    description: str
    reported_date: datetime


class SoldFaultyChassisResponse(BaseModel):
    chassis_number: str
    invoice_number: str
    customer_name: str
    faults: list[SoldFaultyFaultBrief]


# ====================== الفاتورة ======================
class InvoiceCreate(StrippedBaseModel):
    customer_id: int
    items: list[InvoiceItemCreate]
    discount_type: str | None = None
    discount_value: Decimal | None = None
    notes: str | None = None
    invoice_date: datetime | None = None
    initial_payment_amount: Decimal | None = None
    initial_payment_method: str | None = None
    # مبلغ يُستخدم من رصيد العميل كجزء من الدفعة الأولى عند الإنشاء
    use_credit_amount: Decimal | None = None


class InvoiceCancel(StrippedBaseModel):
    reason: str | None = None
    confirm_no_reason: bool = False
    confirm_refund: bool = False


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    invoice_year: int
    invoice_seq: int
    customer_id: int
    customer_name: str | None = None
    invoice_date: datetime
    status: str
    subtotal: Decimal
    discount_type: str | None = None
    discount_value: Decimal | None = None
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    notes: str | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    created_by_username: str | None = None
    cancelled_by_username: str | None = None
    items: list[InvoiceItemResponse] = []
    payments: list[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedInvoices(BaseModel):
    items: list[InvoiceResponse]
    total: int


# ====================== رصيد العميل ======================
class CreditDeposit(StrippedBaseModel):
    amount: Decimal
    notes: str | None = None


class CreditAdjust(StrippedBaseModel):
    new_balance: Decimal
    notes: str


class CreditRefundMark(StrippedBaseModel):
    amount: Decimal


class CreditReallocate(StrippedBaseModel):
    target_invoice_id: int
    amount: Decimal


class CreditActionResponse(BaseModel):
    id: int
    action_type: str
    amount: Decimal
    balance_after: Decimal
    related_invoice_number: str | None = None
    notes: str | None = None
    created_by_username: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerCreditSummary(BaseModel):
    customer_id: int
    customer_name: str
    credit_balance: Decimal


class CustomerCreditBalanceResponse(BaseModel):
    customer_id: int
    credit_balance: Decimal


# 🆕 سجل الاسترجاعات النقدية الفعلية (الخارجة من النظام) — يحلّ محل نظام
# "المدفوعات المعلقة" القديم بالكامل. مصدره الوحيد: CustomerCreditAction
# بنوع action_type == "refunded" (أي زر "استرجاع نقدي" من رصيد أي عميل).
class CreditRefundLogResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    amount: Decimal
    notes: str | None = None
    created_by_username: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCreditRefunds(BaseModel):
    items: list[CreditRefundLogResponse]
    total: int


# ====================== كشف حساب عميل ======================
class CustomerStatementResponse(BaseModel):
    customer_id: int
    customer_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    # 🆕 رصيد العميل الحالي وسجل حركاته الكامل
    credit_balance: Decimal = Decimal("0")
    credit_ledger: list[CreditActionResponse] = []
    invoices: list[InvoiceResponse]


# ====================== إحصائيات لوحة المدير ======================
class MonthlyRevenuePoint(BaseModel):
    month: str
    revenue: Decimal
    invoices_count: int


class InvoiceStatsResponse(BaseModel):
    today_revenue: Decimal
    today_count: int
    week_revenue: Decimal
    week_count: int
    month_revenue: Decimal
    month_count: int
    year_revenue: Decimal
    year_count: int
    total_billed: Decimal
    total_collected: Decimal
    total_refunded: Decimal
    # 🆕 مجموع أرصدة كل العملاء الحاليين (المحفظة الداخلية) — حقل إجباري
    # في هذا الـ response_model، لذا لو لم يُرسله الـ crud سيرفض FastAPI
    # الاستجابة بخطأ 500 واضح بدل أن يُسقطها بصمت — هذا يضمن اكتشاف أي
    # قطع لاحق في السلسلة فورًا بدل أن يظهر كصفر صامت في الواجهة
    total_credit_balance: Decimal
    total_gross_collected: Decimal
    total_outstanding: Decimal
    monthly_breakdown: list[MonthlyRevenuePoint]


class AvailableChassisResponse(BaseModel):
    chassis_number: str
    bike_type_name: str | None = None
    default_price: Decimal | None = None