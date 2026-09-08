from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
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


def create_invoice(db: Session, data: schemas.InvoiceCreate, current_user_id: int):
    if not data.items:
        raise HTTPException(status_code=422, detail="⛔ يجب إضافة بند واحد على الأقل للفاتورة")

    customer = db.query(app_models.Customer).filter(
        app_models.Customer.id == data.customer_id,
        app_models.Customer.is_deleted == False
    ).first()
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

    has_initial_payment = bool(data.initial_payment_amount and data.initial_payment_amount > 0)
    if has_initial_payment and data.initial_payment_amount > total_amount:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ الدفعة الأولية ({data.initial_payment_amount}) أكبر من إجمالي الفاتورة ({total_amount})"
        )

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

    if has_initial_payment:
        db.add(models.Payment(
            invoice_id=invoice.id,
            amount=data.initial_payment_amount,
            payment_method=data.initial_payment_method,
            recorded_by_id=current_user_id,
        ))
        invoice.paid_amount = data.initial_payment_amount
        invoice.remaining_amount = total_amount - data.initial_payment_amount
        invoice.status = "paid" if invoice.remaining_amount <= 0 else "partially_paid"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="🚫 تعارض أثناء إنشاء الفاتورة (رقم مكرر أو هيكل مباع للتو). يرجى المحاولة مجدداً."
        )

    db.refresh(invoice)
    audit_crud.log_action(
        db, "create", "invoice", invoice.id, current_user_id,
        entity_label=f"{invoice.invoice_number} — {customer.name}" + (
            f" (بدفعة أولية {data.initial_payment_amount})" if has_initial_payment else ""
        )
    )
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
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="⛔ قيمة الدفعة يجب أن تكون أكبر من صفر")
    if data.amount > invoice.remaining_amount:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ قيمة الدفعة ({data.amount}) أكبر من المبلغ المتبقي ({invoice.remaining_amount})"
        )

    payment = models.Payment(
        invoice_id=invoice.id,
        amount=data.amount,
        payment_method=data.payment_method,
        notes=data.notes,
        recorded_by_id=current_user_id,
        **({"payment_date": data.payment_date} if data.payment_date else {})
    )
    db.add(payment)

    invoice.paid_amount = invoice.paid_amount + data.amount
    invoice.remaining_amount = invoice.total_amount - invoice.paid_amount
    invoice.status = "paid" if invoice.remaining_amount <= 0 else "partially_paid"

    db.commit()
    db.refresh(payment)
    db.refresh(invoice)

    audit_crud.log_action(
        db, "create", "payment", payment.id, current_user_id,
        entity_label=f"{invoice.invoice_number} — دفعة {data.amount}"
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


# 🆕 حذف دفعة بالكامل (تصحيح خطأ إدخال، وليست عملية استرجاع) — لا تترك أي
# أثر في سجل الفاتورة عمدًا (بعكس فلسفة عدم الحذف الفعلي للأحداث التجارية
# الحقيقية)، لأن هذه أصلاً ليست حدثًا ماليًا وقع فعلاً بل خطأ تسجيل يُصحَّح.
# 🛡️ الحماية من الحذف العرضي لدفعة "حقيقية مكتملة": الفاتورة المدفوعة بالكامل
# (status == paid) مقفلة أصلاً بالكامل (راجع أعلى)، فلا يمكن الوصول لهذا
# المسار إلا على فاتورة partially_paid — يبقى تأكيد إضافي في الواجهة مطلوبًا.
def delete_payment(db: Session, invoice_id: int, payment_id: int, current_user_id: int):
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

    old_discount_amount = invoice.subtotal - invoice.total_amount

    if data.unit_price is not None:
        if data.unit_price <= 0:
            raise HTTPException(status_code=422, detail="⛔ السعر يجب أن يكون أكبر من صفر")

        price_diff = data.unit_price - item.unit_price
        item.unit_price = data.unit_price
        invoice.subtotal = invoice.subtotal + price_diff
        if invoice.subtotal < 0:
            invoice.subtotal = Decimal("0")

        new_total = invoice.subtotal - old_discount_amount
        if new_total < 0:
            new_total = Decimal("0")
        invoice.total_amount = new_total
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


# 🆕 حذف بند فاتورة بشكل عادي (تصحيح خطأ إدخال — مثل إضافة دراجة خاطئة
# للفاتورة)، وليست عملية إرجاع (لا علاقة له بـ ChassisReturn ولا يُفتح عطل).
# البند يُحذف فعليًا من الجدول (بعكس فلسفة عدم الحذف للأحداث التجارية
# الحقيقية، لأن هذا خطأ تسجيل يُصحَّح وليس حدثًا وقع فعلاً).
# 🛡️ إن كان هذا آخر بند في الفاتورة، يتطلب تأكيدًا صريحًا (confirm_delete_invoice)
# لأن حذفه سيُلغي الفاتورة بالكامل تلقائيًا (بنفس منطق الإلغاء عند الإرجاع
# الكامل)، وأي مبلغ مدفوع مسبقًا يظهر تلقائيًا في "المدفوعات المعلقة".
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

    # 🆕🛡️ حذف آخر بند له مساران مختلفان جوهريًا:
    #
    # 1) بلا أي مدفوعات: الفاتورة لم "تحدث" ماليًا بعد إطلاقًا — فلا معنى
    #    لإبقائها كسجل فارغ لا يحمل أي معلومة (لا بند ولا مبلغ). هذا الاستثناء
    #    الوحيد المتعمَّد في كامل النظام لحذف فعلي (Hard Delete) للفاتورة
    #    نفسها، لأنه لا يوجد أثر مالي حقيقي يستحق الحفظ أصلاً.
    #
    # 2) توجد مدفوعات فعلية: تبقى الفاتورة (ملغاة) إلزاميًا كسجل تاريخي —
    #    لكن يجب توثيق لقطة عن البند المحذوف (رقم الهيكل وسعره) داخل
    #    cancel_reason، وإلا يصبح "المبلغ المدفوع" الظاهر لاحقًا في
    #    "المدفوعات المعلقة" بلا أي مرجعية توضح مقابل ماذا دُفع فعليًا.
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
                f"({invoice.paid_amount}) تلقائيًا لقائمة 'المدفوعات المعلقة' لمعالجته. "
                f"هل تريد المتابعة؟"
            ),
            headers={"X-Confirm-Required": "true"},
        )

    chassis_number = item.chassis_number
    deleted_item_price = item.unit_price
    old_discount_amount = invoice.subtotal - invoice.total_amount

    invoice.subtotal = invoice.subtotal - item.unit_price
    if invoice.subtotal < 0:
        invoice.subtotal = Decimal("0")

    new_total = invoice.subtotal - old_discount_amount
    if new_total < 0:
        new_total = Decimal("0")
    invoice.total_amount = new_total
    invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)

    db.delete(item)
    db.flush()

    remaining_items_count = total_items_count - 1
    auto_cancelled = False

    if remaining_items_count <= 0:
        invoice.status = "cancelled"
        invoice.cancelled_at = func.now()
        # 🆕 لقطة توثيقية تحفظ رقم الهيكل وسعره داخل سبب الإلغاء نفسه، حتى
        # يبقى واضحًا دائمًا مقابل أي بند دُفع المبلغ الظاهر لاحقًا كمُسترجَع
        invoice.cancel_reason = (
            f"حذف البند الوحيد في الفاتورة (تصحيح خطأ إدخال) — "
            f"البند المحذوف: {chassis_number} بسعر {deleted_item_price}"
        )
        invoice.cancelled_by_id = current_user_id
        auto_cancelled = True
    else:
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
        audit_label += " — ⚠️ أُلغيت الفاتورة تلقائيًا (كانت البند الوحيد، وتوجد مدفوعات سابقة)"

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
            detail=f"⚠️ هذه الفاتورة عليها مبلغ مدفوع ({invoice.paid_amount}). يرجى تأكيد أنك ستقوم بمعالجته (استرجاع أو نقل لفاتورة أخرى) لاحقًا."
        )

    invoice.status = "cancelled"
    invoice.cancelled_at = func.now()
    invoice.cancel_reason = reason or None
    invoice.cancelled_by_id = current_user_id

    db.commit()
    db.refresh(invoice)

    audit_crud.log_action(
        db, "cancel", "invoice", invoice.id, current_user_id,
        entity_label=invoice.invoice_number, details=invoice.cancel_reason
    )
    return _attach_invoice_extras(db, [invoice])[0]


def _get_processed_amount(db: Session, invoice_id: int) -> Decimal:
    total = db.query(func.sum(models.PaymentRefundAction.amount)).filter(
        models.PaymentRefundAction.invoice_id == invoice_id
    ).scalar()
    return total or Decimal("0")


def _invoice_refundable_pool(invoice: models.Invoice) -> Decimal:
    if invoice.status == "cancelled":
        return invoice.paid_amount
    return max(Decimal("0"), invoice.paid_amount - invoice.total_amount)


def get_pending_invoice_refunds(db: Session):
    candidates = (
        db.query(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .filter(models.Invoice.is_deleted == False)
        .filter(or_(models.Invoice.status == "cancelled", models.Invoice.paid_amount > models.Invoice.total_amount))
        .filter(models.Invoice.paid_amount > 0)
        .order_by(desc(models.Invoice.id))
        .all()
    )
    if not candidates:
        return []

    ids = [i.id for i in candidates]
    processed_rows = (
        db.query(models.PaymentRefundAction.invoice_id, func.sum(models.PaymentRefundAction.amount))
        .filter(models.PaymentRefundAction.invoice_id.in_(ids))
        .group_by(models.PaymentRefundAction.invoice_id)
        .all()
    )
    processed_map = {iid: (amt or Decimal("0")) for iid, amt in processed_rows}

    result = []
    for inv in candidates:
        pool = _invoice_refundable_pool(inv)
        processed = processed_map.get(inv.id, Decimal("0"))
        remaining = pool - processed
        # 🆕 يبقى ظاهرًا في "المعلّقة" طالما لم تكتمل معالجته 100% — حتى لو
        # عليه إجراءات جزئية سبق أن ظهرت أيضًا في "المسترجعة" (راجع الدالة
        # التالية)، فالفاتورة قد تظهر في القائمتين معًا أثناء المعالجة الجزئية
        if remaining <= 0:
            continue
        result.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_status": inv.status,
            "customer_id": inv.customer_id,
            "customer_name": inv.customer.name if inv.customer else "غير معروف",
            "paid_amount": pool,
            "processed_amount": processed,
            "remaining_unprocessed": remaining,
            "cancelled_at": inv.cancelled_at,
        })
    return result


def get_resolved_invoice_refunds(db: Session):
    candidates = (
        db.query(models.Invoice)
        .options(joinedload(models.Invoice.customer))
        .filter(models.Invoice.is_deleted == False)
        .filter(or_(models.Invoice.status == "cancelled", models.Invoice.paid_amount > models.Invoice.total_amount))
        .filter(models.Invoice.paid_amount > 0)
        .order_by(desc(models.Invoice.id))
        .all()
    )
    if not candidates:
        return []

    ids = [i.id for i in candidates]
    actions = (
        db.query(models.PaymentRefundAction)
        .options(joinedload(models.PaymentRefundAction.target_invoice))
        .filter(models.PaymentRefundAction.invoice_id.in_(ids))
        .order_by(models.PaymentRefundAction.created_at)
        .all()
    )
    actions_by_invoice = {}
    for a in actions:
        actions_by_invoice.setdefault(a.invoice_id, []).append(a)

    result = []
    for inv in candidates:
        pool = _invoice_refundable_pool(inv)
        inv_actions = actions_by_invoice.get(inv.id, [])

        # 🆕🛡️ الإصلاح الجوهري: قبل كان يُشترط processed >= pool (معالجة
        # كاملة 100%) قبل الظهور هنا إطلاقًا، فتبقى أي معالجة جزئية غير
        # مرئية في هذا التبويب حتى تكتمل بالكامل دفعة واحدة أو مجزأة —
        # الآن: أي فاتورة عليها إجراء واحد على الأقل تظهر فورًا، وتتراكم
        # الإجراءات في نفس السطر لحظة تسجيلها، بغض النظر عن اكتمال المعالجة
        if not inv_actions:
            continue

        processed = sum((a.amount for a in inv_actions), Decimal("0"))
        result.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_name": inv.customer.name if inv.customer else "غير معروف",
            "paid_amount": pool,
            "fully_resolved": processed >= pool,
            "actions": [
                {
                    "action_type": a.action_type,
                    "amount": a.amount,
                    "target_invoice_number": a.target_invoice.invoice_number if a.target_invoice else None,
                    "created_at": a.created_at,
                }
                for a in inv_actions
            ],
        })
    return result


def mark_invoice_refunded(db: Session, invoice_id: int, amount: Decimal, current_user_id: int):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id, models.Invoice.is_deleted == False
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")

    pool = _invoice_refundable_pool(invoice)
    if pool <= 0:
        raise HTTPException(status_code=400, detail="لا يوجد مبلغ قابل للاسترجاع على هذه الفاتورة")

    processed = _get_processed_amount(db, invoice.id)
    remaining = pool - processed
    if amount <= 0:
        raise HTTPException(status_code=422, detail="⛔ المبلغ يجب أن يكون أكبر من صفر")
    if amount > remaining:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ المبلغ ({amount}) أكبر من المتبقي غير المُعالَج ({remaining})"
        )

    db.add(models.PaymentRefundAction(
        invoice_id=invoice.id,
        action_type="refunded",
        amount=amount,
        created_by_id=current_user_id,
    ))
    db.commit()

    new_processed = processed + amount
    audit_crud.log_action(
        db, "update", "invoice", invoice.id, current_user_id,
        entity_label=f"{invoice.invoice_number} — تسجيل استرجاع {amount} (متبقٍ {pool - new_processed})"
    )
    return {
        "invoice_id": invoice.id,
        "processed_amount": new_processed,
        "remaining_unprocessed": pool - new_processed,
        "resolved": new_processed >= pool,
    }


def reallocate_invoice_refund(db: Session, invoice_id: int, data: schemas.InvoiceRefundReallocate, current_user_id: int):
    source_invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id, models.Invoice.is_deleted == False
    ).first()
    if not source_invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")

    pool = _invoice_refundable_pool(source_invoice)
    if pool <= 0:
        raise HTTPException(status_code=400, detail="لا يوجد مبلغ قابل للاسترجاع على هذه الفاتورة")

    processed = _get_processed_amount(db, source_invoice.id)
    remaining = pool - processed
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="⛔ المبلغ يجب أن يكون أكبر من صفر")
    if data.amount > remaining:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ المبلغ ({data.amount}) أكبر من المتبقي غير المُعالَج ({remaining})"
        )

    target_invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == data.target_invoice_id, models.Invoice.is_deleted == False)
        .with_for_update()
        .first()
    )
    if not target_invoice:
        raise HTTPException(status_code=404, detail="الفاتورة الهدف غير موجودة")
    if target_invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="لا يمكن النقل إلى فاتورة ملغاة")
    if target_invoice.customer_id != source_invoice.customer_id:
        raise HTTPException(status_code=400, detail="يجب أن تكون الفاتورة الهدف لنفس عميل الفاتورة الأصلية")
    if data.amount > target_invoice.remaining_amount:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ المبلغ ({data.amount}) أكبر من المتبقي على الفاتورة الهدف ({target_invoice.remaining_amount})"
        )

    db.add(models.Payment(
        invoice_id=target_invoice.id,
        amount=data.amount,
        payment_method=f"نقل من فاتورة {source_invoice.invoice_number}",
        recorded_by_id=current_user_id,
    ))

    target_invoice.paid_amount = target_invoice.paid_amount + data.amount
    target_invoice.remaining_amount = target_invoice.total_amount - target_invoice.paid_amount
    target_invoice.status = "paid" if target_invoice.remaining_amount <= 0 else "partially_paid"

    db.add(models.PaymentRefundAction(
        invoice_id=source_invoice.id,
        action_type="reallocated",
        amount=data.amount,
        target_invoice_id=target_invoice.id,
        created_by_id=current_user_id,
    ))

    db.commit()

    new_processed = processed + data.amount
    audit_crud.log_action(
        db, "update", "invoice", source_invoice.id, current_user_id,
        entity_label=f"نقل {data.amount} من {source_invoice.invoice_number} إلى {target_invoice.invoice_number} (متبقٍ {pool - new_processed})"
    )
    return {
        "invoice_id": source_invoice.id,
        "processed_amount": new_processed,
        "remaining_unprocessed": pool - new_processed,
        "resolved": new_processed >= pool,
    }


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
    invoices = _attach_invoice_extras(db, invoices)

    total_invoiced = sum((inv.total_amount for inv in invoices), Decimal("0"))
    total_paid = sum((inv.paid_amount for inv in invoices), Decimal("0"))
    total_remaining = total_invoiced - total_paid

    all_customer_invoices = db.query(models.Invoice).filter(
        models.Invoice.customer_id == customer_id,
        models.Invoice.is_deleted == False,
        models.Invoice.paid_amount > 0,
    ).all()
    pending_candidates = [
        inv for inv in all_customer_invoices
        if inv.status == "cancelled" or inv.paid_amount > inv.total_amount
    ]
    total_pending_refund = Decimal("0")
    if pending_candidates:
        ids = [i.id for i in pending_candidates]
        processed_rows = (
            db.query(models.PaymentRefundAction.invoice_id, func.sum(models.PaymentRefundAction.amount))
            .filter(models.PaymentRefundAction.invoice_id.in_(ids))
            .group_by(models.PaymentRefundAction.invoice_id)
            .all()
        )
        processed_map = {iid: (amt or Decimal("0")) for iid, amt in processed_rows}
        total_pending_refund = sum(
            (max(Decimal("0"), _invoice_refundable_pool(inv) - processed_map.get(inv.id, Decimal("0"))) for inv in pending_candidates),
            Decimal("0")
        )

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_remaining": total_remaining,
        "total_pending_refund": total_pending_refund,
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

    old_discount_amount = invoice.subtotal - invoice.total_amount

    invoice.subtotal = invoice.subtotal - item.unit_price
    if invoice.subtotal < 0:
        invoice.subtotal = Decimal("0")

    new_total = invoice.subtotal - old_discount_amount
    if new_total < 0:
        new_total = Decimal("0")
    invoice.total_amount = new_total
    invoice.remaining_amount = max(Decimal("0"), invoice.total_amount - invoice.paid_amount)

    if invoice.paid_amount <= 0:
        invoice.status = "confirmed"
    elif invoice.paid_amount < invoice.total_amount:
        invoice.status = "partially_paid"
    else:
        invoice.status = "paid"

    ret = models.ChassisReturn(
        invoice_item_id=item.id,
        reason=data.reason,
        related_fault_id=related_fault_id,
        notes=data.notes,
        created_by_id=current_user_id,
    )
    db.add(ret)
    db.flush()

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
    if total_items_count > 0 and returned_items_count >= total_items_count and invoice.status != "cancelled":
        invoice.status = "cancelled"
        invoice.cancelled_at = func.now()
        invoice.cancel_reason = "إرجاع جميع بنود الفاتورة (إلغاء تلقائي)"
        invoice.cancelled_by_id = current_user_id
        auto_cancelled = True

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
        "created_by_username": None,
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
    total_collected = sum((p.amount for p in payments), Decimal("0"))
    total_outstanding = sum((i.remaining_amount for i in invoices), Decimal("0"))

    total_refunded = db.query(func.sum(models.PaymentRefundAction.amount)).filter(
        models.PaymentRefundAction.action_type == "refunded"
    ).scalar() or Decimal("0")

    pending_candidates = db.query(models.Invoice).filter(
        models.Invoice.is_deleted == False,
        models.Invoice.paid_amount > 0,
    ).filter(
        or_(models.Invoice.status == "cancelled", models.Invoice.paid_amount > models.Invoice.total_amount)
    ).all()

    total_pending = Decimal("0")
    if pending_candidates:
        ids = [i.id for i in pending_candidates]
        processed_rows = (
            db.query(models.PaymentRefundAction.invoice_id, func.sum(models.PaymentRefundAction.amount))
            .filter(models.PaymentRefundAction.invoice_id.in_(ids))
            .group_by(models.PaymentRefundAction.invoice_id)
            .all()
        )
        processed_map = {iid: (amt or Decimal("0")) for iid, amt in processed_rows}
        total_pending = sum(
            (max(Decimal("0"), _invoice_refundable_pool(inv) - processed_map.get(inv.id, Decimal("0"))) for inv in pending_candidates),
            Decimal("0")
        )

    total_gross_collected = total_collected + total_refunded + total_pending

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
        "total_pending": total_pending,
        "total_gross_collected": total_gross_collected,
        "total_outstanding": total_outstanding,
        "monthly_breakdown": monthly_breakdown,
    }