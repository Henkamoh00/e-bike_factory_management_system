from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from datetime import datetime, timedelta
import calendar
from fastapi import HTTPException
from app import models as app_models, audit_crud, chassis_crud
from . import models, schemas


STARTING_SEQ_OFFSET = 1845  # أول فاتورة = 1845 + 1 = 1846

LOCKED_INVOICE_MESSAGE = (
    "🔒 هذه الفاتورة مدفوعة بالكامل، وبالتالي جميع التعديلات عليها (الدفعات "
    "والبنود) مقفلة تلقائيًا لحماية الأثر المالي. يمكنك فقط إلغاءها أو "
    "تسجيل إرجاع دراجة منها إن لزم الأمر."
)


def generate_invoice_number(db: Session, year: int) -> tuple[int, str]:
    counter = (
        db.query(models.InvoiceNumberCounter)
        .filter(models.InvoiceNumberCounter.year == year)
        .with_for_update()
        .first()
    )

    if not counter:
        counter = models.InvoiceNumberCounter(year=year, last_seq=0)
        db.add(counter)
        db.flush()

    raw_next = counter.last_seq + 1
    actual_seq = raw_next + STARTING_SEQ_OFFSET if counter.last_seq == 0 else raw_next
    counter.last_seq = actual_seq

    invoice_number = f"INV-{year}-{actual_seq:06d}"
    return actual_seq, invoice_number


# ====================== مساعد داخلي لتسجيل حركة على رصيد العميل ======================
def _record_credit_action(
    db: Session,
    customer: app_models.Customer,
    amount: Decimal,
    action_type: str,
    current_user_id: int | None,
    related_invoice_id: int | None = None,
    notes: str | None = None,
):
    """
    يُحدِّث customer.credit_balance مباشرة (لا يعمل commit هنا عمدًا — يبقى
    ضمن نفس معاملة الاستدعاء الأصلية) ويُضيف سجل CustomerCreditAction يوثّق
    الحركة. amount موجب = إضافة، سالب = خصم.
    """
    current_balance = customer.credit_balance or Decimal("0")
    new_balance = current_balance + amount
    if new_balance < 0:
        new_balance = Decimal("0")
    customer.credit_balance = new_balance

    action = models.CustomerCreditAction(
        customer_id=customer.id,
        action_type=action_type,
        amount=amount,
        balance_after=new_balance,
        related_invoice_id=related_invoice_id,
        notes=notes,
        created_by_id=current_user_id,
    )
    db.add(action)
    return action


# 🆕🛡️ يُحسب الخصم دومًا "من جديد" مباشرة من (discount_type, discount_value)
# مقابل subtotal الحالي، بدل استنتاجه عكسيًا من (subtotal - total_amount)
# القديمين. discount_type و discount_value لا يتغيران أبدًا بعد إنشاء
# الفاتورة، لذا هذه الدالة تُعطي دومًا القيمة الصحيحة للخصم بغض النظر عن
# أي تعديلات لاحقة على subtotal أو عن أي إرجاع/حذف بنود.
def _compute_discount_amount(invoice: models.Invoice) -> Decimal:
    if invoice.discount_type == "percentage" and invoice.discount_value:
        return invoice.subtotal * (invoice.discount_value / Decimal("100"))
    elif invoice.discount_type == "fixed" and invoice.discount_value:
        return invoice.discount_value
    return Decimal("0")


# مجموع أسعار البنود المُرجَعة فقط لهذه الفاتورة (تُخصَم من الإجمالي كسطر
# منفصل وواضح، بينما تبقى محسوبة ضمن subtotal لأنها لا تزال "ظاهرة" في
# الفاتورة بعلامة "مُرجَع" وليست محذوفة منها).
def _get_returned_total(db: Session, invoice_id: int) -> Decimal:
    total = (
        db.query(func.sum(models.InvoiceItem.unit_price))
        .join(models.ChassisReturn, models.ChassisReturn.invoice_item_id == models.InvoiceItem.id)
        .filter(models.InvoiceItem.invoice_id == invoice_id)
        .scalar()
    )
    return total or Decimal("0")


# 🆕🛡️🛡️ الإصلاح الجذري لمشكلة "المدفوع يتجاوز الإجمالي": تُستدعى بعد أي
# تعديل على total_amount (تعديل سعر بند، حذف بند، إرجاع). تنقل كامل الفائض
# (وليس فرقًا/delta) دفعة واحدة لرصيد العميل، وتُخفِّض paid_amount نفسه على
# الفاتورة ليصبح مساويًا لـ total_amount بالضبط — بحيث يبقى المدفوع ≤
# الإجمالي دائمًا لهذه الفاتورة تحديدًا، بغض النظر عن أي فائض متراكم سابقًا
# (حتى لو كان الفائض ناتجًا عن بيانات قديمة سابقة لهذا الإصلاح — تُصحَّح
# تلقائيًا في أول عملية تالية تمر عبر هذه الدالة).
def _settle_invoice_surplus(
    db: Session,
    invoice: models.Invoice,
    current_user_id: int | None,
    action_type: str,
    notes: str,
) -> Decimal:
    excess = invoice.paid_amount - invoice.total_amount
    if excess <= 0:
        return Decimal("0")

    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == invoice.customer_id)
        .with_for_update()
        .first()
    )
    if customer:
        _record_credit_action(
            db, customer, excess, action_type, current_user_id,
            related_invoice_id=invoice.id, notes=notes
        )
    invoice.paid_amount = invoice.total_amount
    return excess


# 🆕🛡️ تصحيح ذاتي عند القراءة: فواتير قديمة (من قبل تطبيق _settle_invoice_surplus
# أعلاه) قد يكون مخزَّنًا فيها paid_amount أعلى فعليًا من total_amount —
# فائض حدث وقته ولم يُحوَّل للرصيد بسبب الكود القديم. عند أول قراءة لهذه
# الفاتورة بعد هذا التحديث، تُستخدم _settle_invoice_surplus لتصحيحها فورًا
# (نقل الفائض للرصيد + خفض المدفوع + تصحيح الحالة)، فتتوافق البيانات
# القديمة مع القاعدة الجديدة تلقائيًا دون الحاجة لسكربت هجرة منفصل، ودون
# أن تبقى الفاتورة "مقفلة" بحالة paid خاطئة تمنع أي تصحيح يدوي لاحق.
def _heal_invoice_surplus_if_needed(db: Session, invoice: models.Invoice):
    if invoice.status == "cancelled":
        return
    if invoice.paid_amount <= invoice.total_amount:
        return

    transferred = _settle_invoice_surplus(
        db, invoice, None, "from_adjustment",
        f"تصحيح تلقائي لفائض قديم على الفاتورة {invoice.invoice_number} (بيانات سابقة لتحديث حساب الفائض)"
    )
    if transferred <= 0:
        return

    invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)
    if invoice.paid_amount <= 0:
        invoice.status = "confirmed"
    elif invoice.paid_amount < invoice.total_amount:
        invoice.status = "partially_paid"
    else:
        invoice.status = "paid"

    db.commit()
    db.refresh(invoice)


def create_invoice(db: Session, data: schemas.InvoiceCreate, current_user_id: int):
    if not data.items:
        raise HTTPException(status_code=422, detail="⛔ يجب إضافة بند واحد على الأقل للفاتورة")

    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == data.customer_id, app_models.Customer.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    chassis_numbers = [item.chassis_number for item in data.items]

    candidate_items = (
        db.query(models.InvoiceItem)
        .join(models.Invoice)
        .filter(
            models.InvoiceItem.chassis_number.in_(chassis_numbers),
            models.Invoice.status != "cancelled",
            models.Invoice.is_deleted == False,
        )
        .with_for_update()
        .all()
    )

    already_invoiced = []
    if candidate_items:
        candidate_ids = [i.id for i in candidate_items]
        returned_ids = {
            r[0] for r in db.query(models.ChassisReturn.invoice_item_id)
            .filter(models.ChassisReturn.invoice_item_id.in_(candidate_ids))
            .all()
        }
        already_invoiced = [i for i in candidate_items if i.id not in returned_ids]

    if already_invoiced:
        conflicting = ", ".join({i.chassis_number for i in already_invoiced})
        raise HTTPException(
            status_code=409,
            detail=f"🚫 الهياكل التالية مُباعة ضمن فاتورة أخرى بالفعل: {conflicting}"
        )

    subtotal = sum((item.unit_price for item in data.items), Decimal("0"))

    discount_amount = Decimal("0")
    if data.discount_type == "percentage" and data.discount_value:
        discount_amount = subtotal * (data.discount_value / Decimal("100"))
    elif data.discount_type == "fixed" and data.discount_value:
        discount_amount = data.discount_value

    total_amount = subtotal - discount_amount
    if total_amount < 0:
        total_amount = Decimal("0")

    # حساب مزيج الدفع (نقدي + رصيد) مع تحديد أي مبلغ نقدي زائد يعود
    # تلقائيًا رصيدًا للعميل بدل رفض العملية
    requested_credit = data.use_credit_amount or Decimal("0")
    if requested_credit < 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الرصيد المستخدم غير صحيحة")
    credit_amount = min(requested_credit, customer.credit_balance or Decimal("0"), total_amount)

    cash_requested = data.initial_payment_amount or Decimal("0")
    if cash_requested < 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الدفعة الأولية غير صحيحة")

    remaining_after_credit = total_amount - credit_amount
    cash_applied = min(cash_requested, remaining_after_credit)
    excess_amount = cash_requested - cash_applied  # فائض نقدي فقط، يعود رصيدًا

    has_initial_payment = credit_amount > 0 or cash_applied > 0

    year = data.invoice_date.year if data.invoice_date else datetime.utcnow().year
    seq, invoice_number = generate_invoice_number(db, year)

    invoice = models.Invoice(
        invoice_year=year,
        invoice_seq=seq,
        invoice_number=invoice_number,
        customer_id=data.customer_id,
        status="confirmed",
        subtotal=subtotal,
        discount_type=data.discount_type,
        discount_value=data.discount_value or Decimal("0"),
        total_amount=total_amount,
        paid_amount=Decimal("0"),
        remaining_amount=total_amount,
        notes=data.notes,
        created_by_id=current_user_id,
        **({"invoice_date": data.invoice_date} if data.invoice_date else {})
    )
    db.add(invoice)
    db.flush()

    for item in data.items:
        db.add(models.InvoiceItem(
            invoice_id=invoice.id,
            chassis_number=item.chassis_number,
            unit_price=item.unit_price,
            notes=item.notes,
        ))

    payment_notes_parts = []

    if has_initial_payment:
        if cash_applied > 0:
            db.add(models.Payment(
                invoice_id=invoice.id,
                amount=cash_applied,
                payment_method=data.initial_payment_method,
                recorded_by_id=current_user_id,
            ))
        if credit_amount > 0:
            db.add(models.Payment(
                invoice_id=invoice.id,
                amount=credit_amount,
                payment_method="من رصيد العميل",
                notes="تسديد من رصيد العميل",
                recorded_by_id=current_user_id,
            ))
        invoice.paid_amount = cash_applied + credit_amount
        invoice.remaining_amount = total_amount - invoice.paid_amount
        invoice.status = "paid" if invoice.remaining_amount <= 0 else "partially_paid"

    if credit_amount > 0:
        _record_credit_action(
            db, customer, -credit_amount, "used_on_invoice", current_user_id,
            related_invoice_id=invoice.id,
            notes=f"تسديد فاتورة {invoice_number} من الرصيد"
        )
        payment_notes_parts.append(f"استُخدم {credit_amount} من رصيد العميل")

    if excess_amount > 0:
        _record_credit_action(
            db, customer, excess_amount, "deposit_excess_payment", current_user_id,
            related_invoice_id=invoice.id,
            notes=f"فائض دفعة نقدية عند إنشاء الفاتورة {invoice_number} أُضيف لرصيد العميل"
        )
        payment_notes_parts.append(f"فائض {excess_amount} أُضيف لرصيد العميل")

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="🚫 تعارض أثناء إنشاء الفاتورة (رقم مكرر أو هيكل مباع للتو). يرجى المحاولة مجدداً."
        )

    db.refresh(invoice)
    label = f"{invoice.invoice_number} — {customer.name}"
    if has_initial_payment:
        label += f" (بدفعة أولية {invoice.paid_amount})"
    if payment_notes_parts:
        label += " — " + "، ".join(payment_notes_parts)

    audit_crud.log_action(db, "create", "invoice", invoice.id, current_user_id, entity_label=label)
    return _attach_invoice_extras(db, [invoice])[0]


def add_payment(db: Session, invoice_id: int, data: schemas.PaymentCreate, current_user_id: int):
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن تسجيل دفعة على فاتورة ملغاة")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail=LOCKED_INVOICE_MESSAGE)

    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == invoice.customer_id)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    requested_credit = data.use_credit_amount or Decimal("0")
    if requested_credit < 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الرصيد المستخدم غير صحيحة")

    remaining_before = invoice.remaining_amount
    credit_amount = min(requested_credit, customer.credit_balance or Decimal("0"), remaining_before)

    cash_amount = data.amount or Decimal("0")
    if cash_amount < 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الدفعة يجب أن تكون صحيحة")

    remaining_after_credit = remaining_before - credit_amount
    cash_applied = min(cash_amount, remaining_after_credit)
    excess_amount = cash_amount - cash_applied  # فائض نقدي يعود رصيدًا تلقائيًا

    total_applied = cash_applied + credit_amount
    if total_applied <= 0:
        raise HTTPException(status_code=422, detail="⛔ يجب إدخال مبلغ نقدي أو استخدام رصيد بقيمة أكبر من صفر")

    payment = None
    credit_payment = None

    if cash_applied > 0:
        payment = models.Payment(
            invoice_id=invoice.id,
            amount=cash_applied,
            payment_method=data.payment_method,
            notes=data.notes,
            recorded_by_id=current_user_id,
            **({"payment_date": data.payment_date} if data.payment_date else {})
        )
        db.add(payment)

    if credit_amount > 0:
        credit_payment = models.Payment(
            invoice_id=invoice.id,
            amount=credit_amount,
            payment_method="من رصيد العميل",
            notes="تسديد من رصيد العميل",
            recorded_by_id=current_user_id,
        )
        db.add(credit_payment)

    invoice.paid_amount = invoice.paid_amount + total_applied
    invoice.remaining_amount = invoice.total_amount - invoice.paid_amount
    invoice.status = "paid" if invoice.remaining_amount <= 0 else "partially_paid"

    notes_parts = []
    if credit_amount > 0:
        _record_credit_action(
            db, customer, -credit_amount, "used_on_invoice", current_user_id,
            related_invoice_id=invoice.id,
            notes=f"تسديد فاتورة {invoice.invoice_number} من الرصيد"
        )
        notes_parts.append(f"استُخدم {credit_amount} من رصيد العميل")

    if excess_amount > 0:
        _record_credit_action(
            db, customer, excess_amount, "deposit_excess_payment", current_user_id,
            related_invoice_id=invoice.id,
            notes=f"فائض دفعة تجاوزت المتبقي على الفاتورة {invoice.invoice_number} أُضيف لرصيد العميل"
        )
        notes_parts.append(f"فائض {excess_amount} أُضيف لرصيد العميل")

    db.commit()
    if payment:
        db.refresh(payment)
    if credit_payment:
        db.refresh(credit_payment)
    db.refresh(invoice)

    label = f"{invoice.invoice_number} — دفعة {total_applied}"
    if notes_parts:
        label += " — " + "، ".join(notes_parts)

    audit_crud.log_action(
        db, "create", "payment", (payment.id if payment else (credit_payment.id if credit_payment else invoice.id)),
        current_user_id, entity_label=label
    )
    return _attach_invoice_extras(db, [invoice])[0]


def update_payment(db: Session, invoice_id: int, payment_id: int, data: schemas.PaymentUpdate, current_user_id: int):
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن تعديل دفعات فاتورة ملغاة")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail=LOCKED_INVOICE_MESSAGE)

    payment = db.query(models.Payment).filter(
        models.Payment.id == payment_id,
        models.Payment.invoice_id == invoice_id,
        models.Payment.is_deleted == False,
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    old_amount = payment.amount
    new_amount = data.amount if data.amount is not None else old_amount

    if new_amount <= 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الدفعة يجب أن تكون أكبر من صفر")

    new_total_paid = invoice.paid_amount - old_amount + new_amount
    if new_total_paid > invoice.total_amount:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ إجمالي المدفوعات بعد التعديل ({new_total_paid}) يتجاوز إجمالي الفاتورة ({invoice.total_amount})"
        )
    if new_total_paid < 0:
        new_total_paid = Decimal("0")

    payment.amount = new_amount
    if data.payment_method is not None:
        payment.payment_method = data.payment_method
    if data.notes is not None:
        payment.notes = data.notes

    invoice.paid_amount = new_total_paid
    invoice.remaining_amount = invoice.total_amount - new_total_paid
    if new_total_paid <= 0:
        invoice.status = "confirmed"
    elif new_total_paid < invoice.total_amount:
        invoice.status = "partially_paid"
    else:
        invoice.status = "paid"

    db.commit()
    db.refresh(payment)
    db.refresh(invoice)

    audit_crud.log_action(
        db, "update", "payment", payment.id, current_user_id,
        entity_label=f"{invoice.invoice_number} — تعديل دفعة إلى {new_amount}"
    )
    return _attach_invoice_extras(db, [invoice])[0]


def delete_payment(db: Session, invoice_id: int, payment_id: int, current_user_id: int):
    """
    حذف دفعة بالكامل (تصحيح خطأ إدخال). ⚠️ لو كانت الدفعة المحذوفة مسجَّلة
    من رصيد العميل (payment_method == "من رصيد العميل")، لا نُعيد المبلغ
    للرصيد تلقائيًا هنا عمدًا — هذا المسار مخصَّص فقط لتصحيح خطأ إدخال
    نقدي عادي.
    """
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن حذف دفعات فاتورة ملغاة")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail=LOCKED_INVOICE_MESSAGE)

    payment = db.query(models.Payment).filter(
        models.Payment.id == payment_id,
        models.Payment.invoice_id == invoice_id,
        models.Payment.is_deleted == False,
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    removed_amount = payment.amount

    new_total_paid = invoice.paid_amount - removed_amount
    if new_total_paid < 0:
        new_total_paid = Decimal("0")

    invoice.paid_amount = new_total_paid
    invoice.remaining_amount = invoice.total_amount - new_total_paid
    invoice.status = "confirmed" if new_total_paid <= 0 else "partially_paid"

    db.delete(payment)
    db.commit()
    db.refresh(invoice)

    audit_crud.log_action(
        db, "delete", "payment", payment_id, current_user_id,
        entity_label=f"{invoice.invoice_number} — حذف دفعة خاطئة بقيمة {removed_amount} (تصحيح إدخال)"
    )
    return _attach_invoice_extras(db, [invoice])[0]


def update_invoice_item(db: Session, invoice_id: int, item_id: int, data: schemas.InvoiceItemUpdate, current_user_id: int):
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن تعديل بنود فاتورة ملغاة")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail=LOCKED_INVOICE_MESSAGE)

    item = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.id == item_id,
        models.InvoiceItem.invoice_id == invoice_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="بند الفاتورة غير موجود")

    already_returned = db.query(models.ChassisReturn).filter(
        models.ChassisReturn.invoice_item_id == item.id
    ).first()
    if already_returned:
        raise HTTPException(status_code=400, detail="🚫 لا يمكن تعديل بند تم إرجاعه مسبقاً")

    if data.unit_price is None and data.notes is None:
        raise HTTPException(status_code=422, detail="⛔ لم يتم إرسال أي تعديل")

    if data.unit_price is not None:
        if data.unit_price <= 0:
            raise HTTPException(status_code=422, detail="⛔ السعر يجب أن يكون أكبر من صفر")

        item.unit_price = data.unit_price
        db.flush()

        # subtotal يُعاد حسابه دومًا من جديد مباشرة من مجموع كل البنود
        # الحالية في قاعدة البيانات، لضمان دقته دائمًا
        invoice.subtotal = db.query(func.sum(models.InvoiceItem.unit_price)).filter(
            models.InvoiceItem.invoice_id == invoice.id
        ).scalar() or Decimal("0")

        discount_amount = _compute_discount_amount(invoice)
        returned_total = _get_returned_total(db, invoice.id)
        new_total = invoice.subtotal - discount_amount - returned_total
        if new_total < 0:
            new_total = Decimal("0")
        invoice.total_amount = new_total

        # 🆕🛡️ ينقل أي فائض ناتج (تعديل السعر قلّل الإجمالي دون المدفوع)
        # فورًا لرصيد العميل، ويخفض المدفوع المسجَّل على الفاتورة نفسها
        # ليبقى ≤ الإجمالي دائمًا
        _settle_invoice_surplus(
            db, invoice, current_user_id, "from_adjustment",
            f"فائض من تعديل سعر بند {item.chassis_number} في الفاتورة {invoice.invoice_number}"
        )

        invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)

        if invoice.paid_amount <= 0:
            invoice.status = "confirmed"
        elif invoice.paid_amount < invoice.total_amount:
            invoice.status = "partially_paid"
        else:
            invoice.status = "paid"

    if data.notes is not None:
        item.notes = data.notes

    db.commit()
    db.refresh(item)
    db.refresh(invoice)

    audit_crud.log_action(
        db, "update", "invoice_item", item.id, current_user_id,
        entity_label=f"{invoice.invoice_number} — تعديل بند {item.chassis_number}"
    )
    return _attach_invoice_extras(db, [invoice])[0]


def delete_invoice_item(
    db: Session,
    invoice_id: int,
    item_id: int,
    current_user_id: int,
    confirm_delete_invoice: bool = False,
):
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن حذف بنود فاتورة ملغاة")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail=LOCKED_INVOICE_MESSAGE)

    item = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.id == item_id,
        models.InvoiceItem.invoice_id == invoice_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="بند الفاتورة غير موجود")

    already_returned = db.query(models.ChassisReturn).filter(
        models.ChassisReturn.invoice_item_id == item.id
    ).first()
    if already_returned:
        raise HTTPException(
            status_code=400,
            detail="🚫 لا يمكن حذف بند تم إرجاعه مسبقاً (هو مُستبعَد من الإجمالي أصلاً)"
        )

    total_items_count = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.invoice_id == invoice.id
    ).count()
    is_last_item = total_items_count <= 1
    has_payments = invoice.paid_amount > 0

    if is_last_item and not has_payments:
        chassis_number = item.chassis_number
        invoice_number = invoice.invoice_number
        db.delete(item)
        db.delete(invoice)
        db.commit()

        audit_crud.log_action(
            db, "delete", "invoice", invoice_id, current_user_id,
            entity_label=(
                f"{invoice_number} — حذف كامل ونهائي (لا مدفوعات ولا بنود "
                f"متبقية بعد حذف {chassis_number})"
            )
        )
        return None

    if is_last_item and has_payments and not confirm_delete_invoice:
        raise HTTPException(
            status_code=409,
            detail=(
                f"⚠️ هذا آخر بند في الفاتورة ({invoice.invoice_number})، وحذفه سيؤدي "
                f"إلى إلغاء الفاتورة بالكامل تلقائيًا، وسينتقل المبلغ المدفوع مسبقًا "
                f"({invoice.paid_amount}) تلقائيًا لرصيد العميل. "
                f"هل تريد المتابعة؟"
            ),
            headers={"X-Confirm-Required": "true"},
        )

    chassis_number = item.chassis_number
    deleted_item_price = item.unit_price

    db.delete(item)
    db.flush()

    # subtotal يُعاد حسابه دومًا من جديد مباشرة من مجموع البنود المتبقية
    # فعليًا (البند المحذوف اختفى نهائيًا، بعكس الإرجاع الذي يُبقي البند
    # ظاهرًا بعلامة "مُرجَع")
    invoice.subtotal = db.query(func.sum(models.InvoiceItem.unit_price)).filter(
        models.InvoiceItem.invoice_id == invoice.id
    ).scalar() or Decimal("0")

    discount_amount = _compute_discount_amount(invoice)
    returned_total = _get_returned_total(db, invoice.id)
    new_total = invoice.subtotal - discount_amount - returned_total
    if new_total < 0:
        new_total = Decimal("0")
    invoice.total_amount = new_total

    remaining_items_count = total_items_count - 1
    auto_cancelled = False
    transferred_amount = Decimal("0")

    if remaining_items_count <= 0:
        invoice.status = "cancelled"
        invoice.cancelled_at = func.now()
        invoice.cancel_reason = (
            f"حذف البند الوحيد في الفاتورة (تصحيح خطأ إدخال) — "
            f"البند المحذوف: {chassis_number} بسعر {deleted_item_price}"
        )
        invoice.cancelled_by_id = current_user_id
        auto_cancelled = True

        # الفاتورة أُلغيت تلقائيًا وعليها مدفوعات سابقة — الفائض بالكامل
        # (paid_amount) يعود رصيدًا للعميل فورًا. الفاتورة الملغاة تُستبعد
        # أصلاً من كل حسابات كشف الحساب، فلا حاجة لتعديل paid_amount نفسه
        # هنا للحفاظ على الأثر التاريخي (بنفس منطق إلغاء الفاتورة اليدوي)
        if invoice.paid_amount and invoice.paid_amount > 0:
            customer = db.query(app_models.Customer).filter(
                app_models.Customer.id == invoice.customer_id
            ).with_for_update().first()
            if customer:
                _record_credit_action(
                    db, customer, invoice.paid_amount, "from_cancel", current_user_id,
                    related_invoice_id=invoice.id,
                    notes=f"فائض من إلغاء تلقائي للفاتورة {invoice.invoice_number} (حذف آخر بند)"
                )
                transferred_amount = invoice.paid_amount
    else:
        # 🆕🛡️ الإصلاح الأساسي: ينقل أي فائض ناتج عن هذا الحذف (المدفوع
        # أصبح أعلى من الإجمالي الجديد الأصغر) فورًا وبالكامل لرصيد
        # العميل، ويخفض المدفوع نفسه على الفاتورة ليبقى ≤ الإجمالي —
        # سابقًا كان هذا يحدث فقط عند حذف آخر بند (حالة auto_cancelled)،
        # بينما حذف بند من فاتورة بها بنود متبقية كان يترك المدفوع مرتفعًا
        # دون تصحيح، فيظهر الدَّين سالبًا خطأً في كشف حساب العميل.
        transferred_amount = _settle_invoice_surplus(
            db, invoice, current_user_id, "from_adjustment",
            f"فائض من حذف بند من الفاتورة {invoice.invoice_number} — البند المحذوف: {chassis_number} بسعر {deleted_item_price}"
        )
        invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)
        if invoice.paid_amount <= 0:
            invoice.status = "confirmed"
        elif invoice.paid_amount < invoice.total_amount:
            invoice.status = "partially_paid"
        else:
            invoice.status = "paid"

    db.commit()
    db.refresh(invoice)

    audit_label = f"{chassis_number} — حذف بند من فاتورة {invoice.invoice_number} (تصحيح خطأ إدخال)"
    if auto_cancelled:
        audit_label += " — ⚠️ أُلغيت الفاتورة تلقائيًا (كانت البند الوحيد)، والمبلغ المدفوع أُضيف لرصيد العميل"
    elif transferred_amount > 0:
        audit_label += f" — أُضيف {transferred_amount} لرصيد العميل (فائض ناتج عن الحذف)"

    audit_crud.log_action(
        db, "delete", "invoice_item", item_id, current_user_id,
        entity_label=audit_label
    )
    return _attach_invoice_extras(db, [invoice])[0]


def cancel_invoice(db: Session, invoice_id: int, data: schemas.InvoiceCancel, current_user_id: int):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id, models.Invoice.is_deleted == False
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="الفاتورة ملغاة مسبقاً")

    reason = (data.reason or "").strip()
    if not reason and not data.confirm_no_reason:
        raise HTTPException(status_code=400, detail="يرجى كتابة سبب الإلغاء أو تأكيد الإلغاء بدون سبب")

    if invoice.paid_amount > 0 and not data.confirm_refund:
        raise HTTPException(
            status_code=400,
            detail=f"⚠️ هذه الفاتورة عليها مبلغ مدفوع ({invoice.paid_amount}). يرجى تأكيد أن هذا المبلغ سيُضاف تلقائيًا لرصيد العميل."
        )

    invoice.status = "cancelled"
    invoice.cancelled_at = func.now()
    invoice.cancel_reason = reason or None
    invoice.cancelled_by_id = current_user_id

    if invoice.paid_amount and invoice.paid_amount > 0:
        customer = (
            db.query(app_models.Customer)
            .filter(app_models.Customer.id == invoice.customer_id)
            .with_for_update()
            .first()
        )
        if customer:
            _record_credit_action(
                db, customer, invoice.paid_amount, "from_cancel", current_user_id,
                related_invoice_id=invoice.id,
                notes=f"فائض من إلغاء الفاتورة {invoice.invoice_number}" + (f" — السبب: {reason}" if reason else "")
            )

    db.commit()
    db.refresh(invoice)

    audit_crud.log_action(
        db, "cancel", "invoice", invoice.id, current_user_id,
        entity_label=invoice.invoice_number, details=invoice.cancel_reason
    )
    return _attach_invoice_extras(db, [invoice])[0]


def _attach_invoice_extras(db: Session, invoices: list):
    all_item_ids = [item.id for inv in invoices for item in inv.items]
    returns_map = {}
    if all_item_ids:
        returns = db.query(models.ChassisReturn).filter(
            models.ChassisReturn.invoice_item_id.in_(all_item_ids)
        ).all()
        returns_map = {r.invoice_item_id: r for r in returns}

    for inv in invoices:
        inv.customer_name = inv.customer.name if inv.customer else "غير معروف"
        inv.created_by_username = inv.created_by.username if inv.created_by else None
        inv.cancelled_by_username = inv.cancelled_by.username if inv.cancelled_by else None
        for p in inv.payments:
            p.recorded_by_username = p.recorded_by.username if p.recorded_by else None
        for item in inv.items:
            ret = returns_map.get(item.id)
            item.is_returned = ret is not None
            item.return_reason = ret.reason if ret else None
    return invoices


def get_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    customer_name: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    query = (
        db.query(models.Invoice)
        .options(
            joinedload(models.Invoice.customer),
            joinedload(models.Invoice.created_by),
            joinedload(models.Invoice.cancelled_by),
            joinedload(models.Invoice.items),
            joinedload(models.Invoice.payments),
        )
        .filter(models.Invoice.is_deleted == False)
    )

    if customer_name:
        query = query.join(app_models.Customer).filter(app_models.Customer.name == customer_name)
    if status:
        query = query.filter(models.Invoice.status == status)
    if search:
        query = query.filter(models.Invoice.invoice_number.ilike(f"%{search}%"))

    total = query.count()
    invoices = query.order_by(desc(models.Invoice.id)).offset(skip).limit(limit).all()

    # 🆕 تصحيح ذاتي لأي فاتورة قديمة تحمل مدفوعًا أعلى من إجمالها فعليًا
    for inv in invoices:
        _heal_invoice_surplus_if_needed(db, inv)

    return _attach_invoice_extras(db, invoices), total


def get_invoice_by_id(db: Session, invoice_id: int):
    invoice = (
        db.query(models.Invoice)
        .options(
            joinedload(models.Invoice.customer),
            joinedload(models.Invoice.created_by),
            joinedload(models.Invoice.cancelled_by),
            joinedload(models.Invoice.items),
            joinedload(models.Invoice.payments),
        )
        .filter(models.Invoice.id == invoice_id, models.Invoice.is_deleted == False)
        .first()
    )
    if not invoice:
        return None

    # 🆕 تصحيح ذاتي عند فتح الفاتورة (المودال/PDF) إن كانت من بيانات قديمة
    _heal_invoice_surplus_if_needed(db, invoice)

    return _attach_invoice_extras(db, [invoice])[0]


def get_customer_statement(db: Session, customer_id: int):
    customer = db.query(app_models.Customer).filter(
        app_models.Customer.id == customer_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    invoices = (
        db.query(models.Invoice)
        .options(
            joinedload(models.Invoice.customer),
            joinedload(models.Invoice.created_by),
            joinedload(models.Invoice.cancelled_by),
            joinedload(models.Invoice.items),
            joinedload(models.Invoice.payments),
        )
        .filter(
            models.Invoice.customer_id == customer_id,
            models.Invoice.is_deleted == False,
            models.Invoice.status != "cancelled",
        )
        .order_by(desc(models.Invoice.invoice_date))
        .all()
    )

    # 🆕 تصحيح ذاتي لكل فاتورة نشطة لهذا العميل قبل حساب المجاميع — هذا هو
    # ما يُصلح بطاقة "المتبقي (الدين)" في كشف الحساب، ويُظهر حركة الرصيد
    # الناتجة في السجل فورًا (نستدعيه قبل جلب credit_ledger أدناه تحديدًا
    # لهذا السبب)
    for inv in invoices:
        _heal_invoice_surplus_if_needed(db, inv)

    invoices = _attach_invoice_extras(db, invoices)

    total_invoiced = sum((inv.total_amount for inv in invoices), Decimal("0"))
    total_paid = sum((inv.paid_amount for inv in invoices), Decimal("0"))

    # "المتبقي" الصحيح هو مجموع المتبقي الفعلي لكل فاتورة على حدة (محصور
    # دومًا بين 0 وما فوق)، وليس طرح إجمالي المدفوع من إجمالي الفواتير
    # دفعة واحدة — الفرق يظهر فقط في حال بقي أي عدم اتساق فردي على مستوى
    # فاتورة واحدة، وهو ما يُغطّى أصلاً الآن بالتصحيح الذاتي أعلاه، لكن هذا
    # السطر يبقى كخط دفاع ثانٍ يمنع أي رقم سالب مهما حدث.
    total_remaining = sum(
        (max(Decimal("0"), inv.remaining_amount) for inv in invoices),
        Decimal("0")
    )

    credit_ledger = get_customer_credit_ledger(db, customer_id)

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_remaining": total_remaining,
        "credit_balance": customer.credit_balance or Decimal("0"),
        "credit_ledger": credit_ledger,
        "invoices": invoices,
    }


def get_available_chassis_with_price(db: Session):
    available_numbers = chassis_crud.get_available_chassis(db)
    if not available_numbers:
        return []

    records = (
        db.query(app_models.AssemblyRecord)
        .options(joinedload(app_models.AssemblyRecord.bike_type))
        .filter(app_models.AssemblyRecord.chassis_number.in_(available_numbers))
        .all()
    )
    records_by_chassis = {}
    for r in records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    result = []
    for cn in available_numbers:
        recs = records_by_chassis.get(cn, [])
        bike_type = next((r.bike_type for r in recs if r.bike_type), None)
        result.append({
            "chassis_number": cn,
            "bike_type_name": bike_type.name if bike_type else None,
            "default_price": bike_type.default_price if bike_type else None,
        })
    return result


# ====================== إرجاع الدراجات المباعة ومتابعة الأعطال بعد البيع ======================
def _get_active_invoice_items(db: Session):
    return (
        db.query(models.InvoiceItem)
        .join(models.Invoice)
        .outerjoin(models.ChassisReturn, models.ChassisReturn.invoice_item_id == models.InvoiceItem.id)
        .options(joinedload(models.InvoiceItem.invoice).joinedload(models.Invoice.customer))
        .filter(
            models.Invoice.status != "cancelled",
            models.Invoice.is_deleted == False,
            models.ChassisReturn.id.is_(None),
        )
        .all()
    )


def get_returnable_chassis(db: Session):
    items = _get_active_invoice_items(db)
    return [
        {
            "invoice_item_id": item.id,
            "chassis_number": item.chassis_number,
            "invoice_number": item.invoice.invoice_number,
            "customer_name": item.invoice.customer.name if item.invoice.customer else "غير معروف",
        }
        for item in items
    ]


def get_sold_faulty_chassis(db: Session):
    items = _get_active_invoice_items(db)
    if not items:
        return []

    chassis_numbers = [item.chassis_number for item in items]
    faults = db.query(app_models.Fault).filter(
        app_models.Fault.chassis_number.in_(chassis_numbers),
        app_models.Fault.status == "pending"
    ).order_by(app_models.Fault.reported_date).all()

    faults_by_chassis = {}
    for f in faults:
        faults_by_chassis.setdefault(f.chassis_number, []).append(f)

    result = []
    for item in items:
        item_faults = faults_by_chassis.get(item.chassis_number)
        if not item_faults:
            continue
        result.append({
            "chassis_number": item.chassis_number,
            "invoice_number": item.invoice.invoice_number,
            "customer_name": item.invoice.customer.name if item.invoice.customer else "غير معروف",
            "faults": [
                {"id": f.id, "description": f.description, "reported_date": f.reported_date}
                for f in item_faults
            ],
        })
    return result


def create_return(db: Session, data: schemas.ChassisReturnCreate, current_user_id: int):
    item = (
        db.query(models.InvoiceItem)
        .options(joinedload(models.InvoiceItem.invoice).joinedload(models.Invoice.customer))
        .filter(models.InvoiceItem.id == data.invoice_item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="بند الفاتورة غير موجود")

    invoice = item.invoice
    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن تسجيل إرجاع لبند على فاتورة ملغاة")

    existing = db.query(models.ChassisReturn).filter(
        models.ChassisReturn.invoice_item_id == item.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="تم تسجيل إرجاع هذا البند مسبقاً")

    related_fault_id = data.related_fault_id
    auto_created_fault = False

    if data.related_fault_id:
        fault = db.query(app_models.Fault).filter(
            app_models.Fault.id == data.related_fault_id,
            app_models.Fault.chassis_number == item.chassis_number,
        ).first()
        if not fault:
            raise HTTPException(status_code=404, detail="العطل المرتبط غير موجود أو لا يخص هذا الهيكل")
    elif data.create_fault_stage:
        stage_value = (
            data.create_fault_stage.value
            if hasattr(data.create_fault_stage, "value")
            else data.create_fault_stage
        )
        new_fault = app_models.Fault(
            chassis_number=item.chassis_number,
            description=f"عطل اكتُشف عند إرجاع الدراجة من فاتورة {invoice.invoice_number} — السبب: {data.reason}",
            related_stage=stage_value,
            status="pending",
            reported_by_id=current_user_id,
        )
        db.add(new_fault)
        db.flush()
        related_fault_id = new_fault.id
        auto_created_fault = True

    ret = models.ChassisReturn(
        invoice_item_id=item.id,
        reason=data.reason,
        related_fault_id=related_fault_id,
        notes=data.notes,
        created_by_id=current_user_id,
    )
    db.add(ret)
    db.flush()

    # subtotal لا يُعدَّل أبدًا عند الإرجاع — يبقى دائمًا يحمل مجموع أسعار
    # كل البنود الظاهرة في الفاتورة (الحالية والمُرجَعة معًا)، حتى يتضح
    # للقارئ أن سعر البند المُرجَع مخصوم من الإجمالي الأصلي الكامل
    # للفاتورة. فقط total_amount يُعاد حسابه بطرح كل من الخصم وقيمة كل
    # البنود المُرجَعة من subtotal الثابت.
    discount_amount = _compute_discount_amount(invoice)
    returned_total = _get_returned_total(db, invoice.id)
    new_total = invoice.subtotal - discount_amount - returned_total
    if new_total < 0:
        new_total = Decimal("0")
    invoice.total_amount = new_total

    total_items_count = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.invoice_id == invoice.id
    ).count()
    returned_items_count = (
        db.query(models.ChassisReturn)
        .join(models.InvoiceItem, models.ChassisReturn.invoice_item_id == models.InvoiceItem.id)
        .filter(models.InvoiceItem.invoice_id == invoice.id)
        .count()
    )

    auto_cancelled = False
    transferred_amount = Decimal("0")

    if total_items_count > 0 and returned_items_count >= total_items_count:
        invoice.status = "cancelled"
        invoice.cancelled_at = func.now()
        invoice.cancel_reason = "إرجاع جميع بنود الفاتورة (إلغاء تلقائي)"
        invoice.cancelled_by_id = current_user_id
        auto_cancelled = True

        # الفاتورة أُلغيت بالكامل: كل المبلغ المدفوع فائض الآن، ينتقل
        # بالكامل لرصيد العميل (الفاتورة الملغاة مستبعدة أصلاً من كل
        # حسابات كشف الحساب، فلا حاجة لتعديل paid_amount نفسه)
        if invoice.paid_amount and invoice.paid_amount > 0:
            customer = invoice.customer or db.query(app_models.Customer).filter(
                app_models.Customer.id == invoice.customer_id
            ).with_for_update().first()
            if customer:
                _record_credit_action(
                    db, customer, invoice.paid_amount, "from_return", current_user_id,
                    related_invoice_id=invoice.id,
                    notes=f"فائض من إرجاع جميع بنود الفاتورة {invoice.invoice_number} (إلغاء تلقائي)"
                )
                transferred_amount = invoice.paid_amount
    else:
        # 🆕🛡️ الإصلاح الأساسي: ينقل أي فائض ناتج عن هذا الإرجاع (المدفوع
        # أصبح أعلى من الإجمالي الجديد الأصغر) فورًا وبالكامل لرصيد
        # العميل، ويخفض المدفوع نفسه على الفاتورة ليبقى ≤ الإجمالي
        transferred_amount = _settle_invoice_surplus(
            db, invoice, current_user_id, "from_return",
            f"فائض من إرجاع {item.chassis_number} في الفاتورة {invoice.invoice_number}"
        )
        invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)
        if invoice.paid_amount <= 0:
            invoice.status = "confirmed"
        elif invoice.paid_amount < invoice.total_amount:
            invoice.status = "partially_paid"
        else:
            invoice.status = "paid"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="تم تسجيل إرجاع هذا البند للتو من جهة أخرى")
    db.refresh(ret)
    db.refresh(invoice)

    audit_label = f"{item.chassis_number} — إرجاع من فاتورة {invoice.invoice_number} (خصم {item.unit_price} من الإجمالي تلقائيًا)"
    if auto_created_fault:
        audit_label += f" — فُتح عطل جديد تلقائيًا (#{related_fault_id})"
    if auto_cancelled:
        audit_label += " — ⚠️ أُلغيت الفاتورة تلقائيًا لإرجاع جميع بنودها"
    if transferred_amount > 0:
        audit_label += f" — أُضيف {transferred_amount} لرصيد العميل"

    audit_crud.log_action(
        db, "create", "chassis_return", ret.id, current_user_id,
        entity_label=audit_label,
        details=data.reason
    )

    return {
        "id": ret.id,
        "invoice_item_id": item.id,
        "chassis_number": item.chassis_number,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer.name if invoice.customer else "غير معروف",
        "reason": ret.reason,
        "related_fault_id": ret.related_fault_id,
        "notes": ret.notes,
        "created_by_username": ret.created_by.username if ret.created_by else None,
        "created_at": ret.created_at,
    }


def get_returns(db: Session, skip: int = 0, limit: int = 20):
    query = (
        db.query(models.ChassisReturn)
        .options(
            joinedload(models.ChassisReturn.invoice_item).joinedload(models.InvoiceItem.invoice).joinedload(models.Invoice.customer),
            joinedload(models.ChassisReturn.created_by),
        )
        .order_by(desc(models.ChassisReturn.created_at))
    )
    total = query.count()
    rows = query.offset(skip).limit(limit).all()

    result = []
    for r in rows:
        item = r.invoice_item
        result.append({
            "id": r.id,
            "invoice_item_id": item.id,
            "chassis_number": item.chassis_number,
            "invoice_number": item.invoice.invoice_number,
            "customer_name": item.invoice.customer.name if item.invoice.customer else "غير معروف",
            "reason": r.reason,
            "related_fault_id": r.related_fault_id,
            "notes": r.notes,
            "created_by_username": r.created_by.username if r.created_by else None,
            "created_at": r.created_at,
        })
    return result, total


# ====================== رصيد العميل (المحفظة الداخلية) ======================
def get_customer_credit_ledger(db: Session, customer_id: int):
    actions = (
        db.query(models.CustomerCreditAction)
        .options(
            joinedload(models.CustomerCreditAction.related_invoice),
            joinedload(models.CustomerCreditAction.created_by),
        )
        .filter(models.CustomerCreditAction.customer_id == customer_id)
        .order_by(desc(models.CustomerCreditAction.created_at))
        .all()
    )
    for a in actions:
        a.related_invoice_number = a.related_invoice.invoice_number if a.related_invoice else None
        a.created_by_username = a.created_by.username if a.created_by else None
    return actions


def deposit_customer_credit(db: Session, customer_id: int, data: schemas.CreditDeposit, current_user_id: int):
    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == customer_id, app_models.Customer.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="⛔ المبلغ يجب أن يكون أكبر من صفر")

    _record_credit_action(db, customer, data.amount, "deposit", current_user_id, notes=data.notes)
    db.commit()
    db.refresh(customer)

    audit_crud.log_action(
        db, "update", "customer", customer.id, current_user_id,
        entity_label=f"{customer.name} — إيداع رصيد {data.amount}", details=data.notes
    )
    return {"customer_id": customer.id, "credit_balance": customer.credit_balance}


def adjust_customer_credit(db: Session, customer_id: int, data: schemas.CreditAdjust, current_user_id: int):
    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == customer_id, app_models.Customer.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    if data.new_balance < 0:
        raise HTTPException(status_code=422, detail="⛔ لا يمكن أن يكون الرصيد بالسالب")

    delta = data.new_balance - (customer.credit_balance or Decimal("0"))
    if delta == 0:
        raise HTTPException(status_code=422, detail="⛔ الرصيد الجديد مطابق للرصيد الحالي، لا يوجد تعديل")

    _record_credit_action(db, customer, delta, "manual_adjust", current_user_id, notes=data.notes)
    db.commit()
    db.refresh(customer)

    audit_crud.log_action(
        db, "update", "customer", customer.id, current_user_id,
        entity_label=f"{customer.name} — تعديل يدوي للرصيد إلى {data.new_balance}", details=data.notes
    )
    return {"customer_id": customer.id, "credit_balance": customer.credit_balance}


def credit_mark_refunded(db: Session, customer_id: int, amount: Decimal, current_user_id: int):
    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == customer_id, app_models.Customer.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    if amount <= 0 or amount > (customer.credit_balance or Decimal("0")):
        raise HTTPException(status_code=422, detail=f"⛔ المبلغ غير صحيح (الرصيد المتاح: {customer.credit_balance})")

    _record_credit_action(db, customer, -amount, "refunded", current_user_id, notes="استرجاع نقدي من رصيد العميل")
    db.commit()
    db.refresh(customer)

    audit_crud.log_action(
        db, "update", "customer", customer.id, current_user_id,
        entity_label=f"{customer.name} — استرجاع {amount} من الرصيد نقدًا"
    )
    return {"customer_id": customer.id, "credit_balance": customer.credit_balance}


def credit_reallocate(db: Session, customer_id: int, data: schemas.CreditReallocate, current_user_id: int):
    customer = (
        db.query(app_models.Customer)
        .filter(app_models.Customer.id == customer_id, app_models.Customer.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    target_invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == data.target_invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not target_invoice:
        raise HTTPException(status_code=404, detail="الفاتورة الهدف غير موجودة")
    if target_invoice.customer_id != customer.id:
        raise HTTPException(status_code=400, detail="يجب أن تكون الفاتورة الهدف لنفس العميل")
    if target_invoice.status in ("cancelled", "paid"):
        raise HTTPException(status_code=400, detail="لا يمكن النقل إلى هذه الفاتورة (ملغاة أو مدفوعة بالكامل)")

    amount = data.amount
    if amount <= 0 or amount > (customer.credit_balance or Decimal("0")):
        raise HTTPException(status_code=422, detail=f"⛔ المبلغ غير صحيح (الرصيد المتاح: {customer.credit_balance})")
    if amount > target_invoice.remaining_amount:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ المبلغ أكبر من المتبقي على الفاتورة الهدف ({target_invoice.remaining_amount})"
        )

    db.add(models.Payment(
        invoice_id=target_invoice.id,
        amount=amount,
        payment_method="من رصيد العميل",
        notes="تسديد من رصيد العميل",
        recorded_by_id=current_user_id,
    ))
    target_invoice.paid_amount = target_invoice.paid_amount + amount
    target_invoice.remaining_amount = target_invoice.total_amount - target_invoice.paid_amount
    target_invoice.status = "paid" if target_invoice.remaining_amount <= 0 else "partially_paid"

    _record_credit_action(
        db, customer, -amount, "used_on_invoice", current_user_id,
        related_invoice_id=target_invoice.id,
        notes=f"تسديد فاتورة {target_invoice.invoice_number} من الرصيد"
    )

    db.commit()
    db.refresh(target_invoice)
    db.refresh(customer)

    audit_crud.log_action(
        db, "update", "customer", customer.id, current_user_id,
        entity_label=f"{customer.name} — تسديد {amount} من الرصيد لفاتورة {target_invoice.invoice_number}"
    )
    return {
        "customer_id": customer.id,
        "credit_balance": customer.credit_balance,
        "target_invoice_number": target_invoice.invoice_number,
    }


def get_customers_with_credit(db: Session):
    customers = db.query(app_models.Customer).filter(
        app_models.Customer.is_deleted == False,
        app_models.Customer.credit_balance > 0,
    ).order_by(desc(app_models.Customer.credit_balance)).all()
    return [
        {"customer_id": c.id, "customer_name": c.name, "credit_balance": c.credit_balance}
        for c in customers
    ]


def get_credit_refund_log(db: Session, skip: int = 0, limit: int = 50):
    query = (
        db.query(models.CustomerCreditAction)
        .options(
            joinedload(models.CustomerCreditAction.customer),
            joinedload(models.CustomerCreditAction.created_by),
        )
        .filter(models.CustomerCreditAction.action_type == "refunded")
        .order_by(desc(models.CustomerCreditAction.created_at))
    )
    total = query.count()
    rows = query.offset(skip).limit(limit).all()

    result = []
    for a in rows:
        result.append({
            "id": a.id,
            "customer_id": a.customer_id,
            "customer_name": a.customer.name if a.customer else "غير معروف",
            "amount": abs(a.amount),
            "notes": a.notes,
            "created_by_username": a.created_by.username if a.created_by else None,
            "created_at": a.created_at,
        })
    return result, total


# ====================== إحصائيات لوحة المدير ======================
def get_invoice_stats(db: Session):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = datetime(now.year, now.month, 1)
    year_start = datetime(now.year, 1, 1)

    invoices = db.query(models.Invoice).filter(
        models.Invoice.is_deleted == False,
        models.Invoice.status != "cancelled"
    ).all()

    def _strip_tz(dt):
        return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

    def count_invoices_since(since):
        return len([i for i in invoices if i.invoice_date and _strip_tz(i.invoice_date) >= since])

    today_count = count_invoices_since(today_start)
    week_count = count_invoices_since(week_start)
    month_count = count_invoices_since(month_start)
    year_count = count_invoices_since(year_start)

    payments = (
        db.query(models.Payment)
        .join(models.Invoice)
        .filter(
            models.Payment.is_deleted == False,
            models.Invoice.is_deleted == False,
            models.Invoice.status != "cancelled",
        )
        .all()
    )

    def sum_payments_since(since):
        return sum(
            (p.amount for p in payments if p.payment_date and _strip_tz(p.payment_date) >= since),
            Decimal("0")
        )

    today_revenue = sum_payments_since(today_start)
    week_revenue = sum_payments_since(week_start)
    month_revenue = sum_payments_since(month_start)
    year_revenue = sum_payments_since(year_start)

    total_billed = sum((i.total_amount for i in invoices), Decimal("0"))
    total_collected_payments = sum((p.amount for p in payments), Decimal("0"))
    total_outstanding = sum((i.remaining_amount for i in invoices), Decimal("0"))

    total_refunded_raw = db.query(func.sum(models.CustomerCreditAction.amount)).filter(
        models.CustomerCreditAction.action_type == "refunded"
    ).scalar() or Decimal("0")
    total_refunded = abs(total_refunded_raw)

    # 🆕🛡️🛡️ مجموع أرصدة كل العملاء الحاليين (المحفظة الداخلية).
    # 🛡️ السبب الحقيقي لظهور القيمة صفرًا سابقًا: الفلتر القديم
    # `is_deleted == False` يستبعد بصمت أي عميل قديم قيمة is_deleted عنده
    # NULL (لم تُملأ عند الترحيل)، لأن NULL لا يُطابق أبدًا `== False` في
    # SQL — بينما جلب عميل واحد بالـ id (كما في get_customer_statement) لا
    # يستخدم هذا الفلتر أصلاً، فتظهر أرصدته الفردية بشكل صحيح رغم أن
    # المجموع الكلي يتجاهله. الإصلاح هنا مزدوج:
    # 1) الفلتر أصبح is_deleted.isnot(True) بدل == False، فيُعامل NULL
    #    كـ"غير محذوف" (وهو المنطق السليم أصلاً).
    # 2) الجمع يتم على مستوى بايثون عبر كل عميل على حدة (بنفس أسلوب
    #    customer.credit_balance or Decimal("0") المُستخدم بنجاح في بقية
    #    هذا الملف) بدل الاعتماد على func.sum/coalesce الخام، لتفادي أي
    #    شذوذ محتمل في محرك القاعدة مع عمود Numeric.
    non_deleted_customers = db.query(app_models.Customer.credit_balance).filter(
        app_models.Customer.is_deleted.isnot(True)
    ).all()
    total_credit_balance = sum(
        (Decimal(row[0]) if row[0] is not None else Decimal("0") for row in non_deleted_customers),
        Decimal("0")
    )

    # 🆕 "صافي المحصَّل": من مدفوعات الفواتير فقط (بدون أي جمع للرصيد
    # عليه)، وبدون أي سقف صناعي — لو ظهر يومًا تجاوز حقيقي هنا فهو مؤشر
    # خلل حقيقي يجب أن يظهر وليس أن يُخفى.
    total_collected = total_collected_payments

    # 🆕 "الإجمالي الشامل (كل ما دخل الصندوق)" = صافي المحصَّل + المسترجَع + الأرصدة
    total_gross_collected = total_collected + total_refunded + total_credit_balance

    monthly_breakdown = []
    for i in range(11, -1, -1):
        target_month = (now.month - i - 1) % 12 + 1
        target_year = now.year + ((now.month - i - 1) // 12)
        m_start = datetime(target_year, target_month, 1)
        last_day = calendar.monthrange(target_year, target_month)[1]
        m_end = datetime(target_year, target_month, last_day, 23, 59, 59)

        m_revenue = sum(
            (p.amount for p in payments if p.payment_date and m_start <= _strip_tz(p.payment_date) <= m_end),
            Decimal("0")
        )
        m_invoices_count = len([
            inv for inv in invoices
            if inv.invoice_date and m_start <= _strip_tz(inv.invoice_date) <= m_end
        ])
        monthly_breakdown.append({
            "month": f"{target_year}-{target_month:02d}",
            "revenue": m_revenue,
            "invoices_count": m_invoices_count,
        })

    return {
        "today_revenue": today_revenue, "today_count": today_count,
        "week_revenue": week_revenue, "week_count": week_count,
        "month_revenue": month_revenue, "month_count": month_count,
        "year_revenue": year_revenue, "year_count": year_count,
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_refunded": total_refunded,
        "total_credit_balance": total_credit_balance,
        "total_gross_collected": total_gross_collected,
        "total_outstanding": total_outstanding,
        "monthly_breakdown": monthly_breakdown,
    }