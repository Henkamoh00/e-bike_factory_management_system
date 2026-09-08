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
    amount: Decimal
    payment_method: str | None = None
    payment_date: datetime | None = None
    notes: str | None = None


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


# ====================== معالجة استرجاع المبالغ (على مستوى الفاتورة) ======================
class InvoiceRefundMark(StrippedBaseModel):
    amount: Decimal


class InvoiceRefundReallocate(StrippedBaseModel):
    target_invoice_id: int
    amount: Decimal


class RefundActionResult(BaseModel):
    invoice_id: int
    processed_amount: Decimal
    remaining_unprocessed: Decimal
    resolved: bool


class PendingInvoiceRefundResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    invoice_status: str
    customer_id: int
    customer_name: str
    paid_amount: Decimal
    processed_amount: Decimal
    remaining_unprocessed: Decimal
    cancelled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RefundActionLog(BaseModel):
    action_type: str
    amount: Decimal
    target_invoice_number: str | None = None
    created_at: datetime


class ResolvedInvoiceRefundResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    customer_name: str
    paid_amount: Decimal
    # 🆕 يوضح للواجهة إن كانت المعالجة اكتملت 100% (تُعرض باهتة/مؤرشفة) أو
    # لا تزال جزئية (تُعرض بشكل عادي مع إشارة "معالجة جزئية")، بدل الانتظار
    # حتى الاكتمال الكامل لتظهر الإجراءات المسجَّلة فعليًا
    fully_resolved: bool = True
    actions: list[RefundActionLog]


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


# ====================== كشف حساب عميل ======================
class CustomerStatementResponse(BaseModel):
    customer_id: int
    customer_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    total_pending_refund: Decimal
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
    total_pending: Decimal
    total_gross_collected: Decimal
    total_outstanding: Decimal
    monthly_breakdown: list[MonthlyRevenuePoint]


class AvailableChassisResponse(BaseModel):
    chassis_number: str
    bike_type_name: str | None = None
    default_price: Decimal | None = None