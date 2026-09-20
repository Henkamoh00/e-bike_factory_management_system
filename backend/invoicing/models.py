from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    Numeric, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InvoiceNumberCounter(Base):
    __tablename__ = "invoice_number_counters"

    year = Column(Integer, primary_key=True)
    last_seq = Column(Integer, nullable=False, default=0)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    invoice_year = Column(Integer, nullable=False, index=True)
    invoice_seq = Column(Integer, nullable=False)
    invoice_number = Column(String, nullable=False, unique=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    invoice_date = Column(DateTime(timezone=True), server_default=func.now())

    status = Column(String, nullable=False, default="confirmed", index=True)

    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    discount_type = Column(String, nullable=True)
    discount_value = Column(Numeric(12, 2), nullable=True, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    paid_amount = Column(Numeric(12, 2), nullable=False, default=0)
    remaining_amount = Column(Numeric(12, 2), nullable=False, default=0)

    notes = Column(Text, nullable=True)

    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    customer = relationship("Customer")
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('invoice_year', 'invoice_seq', name='uq_invoice_year_seq'),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    chassis_number = Column(String, nullable=False, index=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    notes = Column(String, nullable=True)

    invoice = relationship("Invoice", back_populates="items")
    # 🆕 علاقة عكسية مع سجل الإرجاع (إن وُجد) — تُستخدم لتحديد is_returned
    # دون أي استعلام إضافي منفصل لكل بند (تُجلب بالجملة في invoices_crud)
    chassis_return = relationship("ChassisReturn", back_populates="invoice_item", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String, nullable=True)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


class PaymentRefundAction(Base):
    __tablename__ = "payment_refund_actions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    # "refunded" | "reallocated" | "credited" (🆕 تحويل تلقائي/يدوي لرصيد العميل)
    action_type = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    target_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    notes = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    target_invoice = relationship("Invoice", foreign_keys=[target_invoice_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class ChassisReturn(Base):
    """
    سجل إرجاع دراجة مباعة بعد الشراء (لأي سبب: عطل أو غيره). لا يُعدَّل
    أو يُحذف أبدًا (أثر دائم متسق مع فلسفة عدم الحذف الفعلي في كامل النظام).
    بمجرد تسجيله، يُعتبر ذلك البند تحديدًا "مُرجَعًا" — ويُعرض كذلك في
    واجهة الفاتورة عبر InvoiceItemResponse.is_returned بدل حذفه أو إخفائه،
    فيعود الهيكل متاحًا للبيع من جديد تلقائيًا (يُستبعد من "المُباع حاليًا"
    في كل الاستعلامات)، دون أي تأثير مالي آلي على الفاتورة الأصلية — أي
    تسوية مالية (استرجاع، خصم، إلخ) تتم يدويًا عبر أدوات الفاتورة الموجودة
    أصلاً إن رغب المدير.
    """
    __tablename__ = "chassis_returns"

    id = Column(Integer, primary_key=True, index=True)
    # 🛡️ فريد: نفس بند الفاتورة (نفس عملية بيع محددة) لا يمكن إرجاعه مرتين
    invoice_item_id = Column(Integer, ForeignKey("invoice_items.id"), nullable=False, unique=True, index=True)
    reason = Column(String, nullable=False)
    # ربط اختياري بعطل مسجَّل مسبقًا لنفس الهيكل (إن كان سبب الإرجاع عطلاً)
    # أو بعطل أُنشئ تلقائيًا لحظة الإرجاع (راجع create_fault_stage في schemas)
    related_fault_id = Column(Integer, ForeignKey("faults.id"), nullable=True)
    notes = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice_item = relationship("InvoiceItem", back_populates="chassis_return")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ====================== 🆕 رصيد العميل (المحفظة الداخلية) ======================
class CustomerCreditAction(Base):
    """
    سجل كل حركة على رصيد العميل (Customer.credit_balance)، سواء تلقائية
    (فائض من إلغاء/إرجاع فاتورة) أو يدوية (إيداع، تعديل، استرجاع نقدي،
    استخدام على فاتورة، نقل لفاتورة أخرى). amount موجب = إضافة للرصيد،
    سالب = خصم منه. balance_after = الرصيد الفعلي بعد هذه الحركة تحديدًا،
    لضمان إمكانية إعادة بناء تاريخ الرصيد الكامل من هذا الجدول وحده.

    action_type الممكنة:
      - "deposit"               إيداع يدوي من الإدارة
      - "manual_adjust"         تصحيح يدوي مباشر للرصيد
      - "from_cancel"           فائض تلقائي من إلغاء فاتورة
      - "from_return"           فائض تلقائي من إرجاع دراجة (تجاوز الدفعات للإجمالي بعد الإرجاع)
      - "used_on_invoice"       استخدام الرصيد كدفعة عند إنشاء/تسجيل دفعة فاتورة
      - "deposit_excess_payment" فائض دفعة نقدية تجاوزت المتبقي على الفاتورة
      - "refunded"               استرجاع نقدي فعلي من الرصيد (خروج من النظام)
      - "reallocated"            نقل جزء من الرصيد لسداد فاتورة أخرى
    """
    __tablename__ = "customer_credit_actions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    related_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    notes = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", foreign_keys=[customer_id])
    related_invoice = relationship("Invoice", foreign_keys=[related_invoice_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
