from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from . import models, schemas, audit_crud


def create_sale(db: Session, sale: schemas.SaleCreate, current_user_id: int):
    existing_active_sale = db.query(models.Sale).filter(
        models.Sale.chassis_number == sale.chassis_number,
        models.Sale.status == "active"
    ).first()

    if existing_active_sale:
        raise ValueError("هذه الدراجة تم بيعها مسبقاً")

    customer = db.query(models.Customer).filter(
        models.Customer.id == sale.customer_id
    ).first()

    if not customer:
        raise ValueError("العميل المحدد غير موجود")

    db_sale = models.Sale(
        chassis_number=sale.chassis_number,
        customer_id=sale.customer_id,
        notes=sale.notes,
        status="active",
        created_by_id=current_user_id,
        **({"sale_date": sale.sale_date} if sale.sale_date else {})
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    audit_crud.log_action(
        db, "create", "sale", db_sale.id, current_user_id,
        entity_label=f"{sale.chassis_number} — {customer.name}"
    )
    return db_sale


def cancel_sale(db: Session, sale_id: int, payload: schemas.SaleCancel, current_user_id: int):
    sale = db.query(models.Sale).filter(models.Sale.id == sale_id).first()
    if not sale:
        raise ValueError("عملية البيع غير موجودة")
    if sale.status == "cancelled":
        raise ValueError("عملية البيع ملغاة مسبقاً")

    reason = (payload.reason or "").strip()
    if not reason and not payload.confirm_no_reason:
        raise ValueError("يرجى كتابة سبب الإلغاء أو تأكيد الإلغاء بدون سبب")

    sale.status = "cancelled"
    sale.cancelled_at = func.now()
    sale.cancel_reason = reason or None
    sale.cancelled_by_id = current_user_id
    db.commit()
    db.refresh(sale)
    audit_crud.log_action(
        db, "cancel", "sale", sale.id, current_user_id,
        entity_label=sale.chassis_number, details=sale.cancel_reason
    )
    return sale


def get_sales(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    customer_name: str | None = None,
    status: str | None = None,
    date_from=None,
    date_to=None,
):
    """🆕 مُصفَّحة الآن مع فلاتر من جهة السيرفر: تُرجع Tuple (items, total)"""
    query = db.query(models.Sale)\
              .options(joinedload(models.Sale.customer))\
              .options(joinedload(models.Sale.created_by))\
              .options(joinedload(models.Sale.cancelled_by))

    if customer_name:
        query = query.join(models.Customer).filter(models.Customer.name == customer_name)
    if status:
        query = query.filter(models.Sale.status == status)
    if date_from:
        query = query.filter(models.Sale.sale_date >= date_from)
    if date_to:
        query = query.filter(models.Sale.sale_date <= date_to)

    total = query.count()
    sales = query.order_by(desc(models.Sale.sale_date)).offset(skip).limit(limit).all()

    for sale in sales:
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"
        sale.created_by_username = sale.created_by.username if sale.created_by else None
        sale.cancelled_by_username = sale.cancelled_by.username if sale.cancelled_by else None

    return sales, total


def bulk_cancel_sales(db: Session, payload: schemas.BulkCancel, current_user_id: int):
    reason = (payload.reason or "").strip()
    if not reason and not payload.confirm_no_reason:
        raise ValueError("يرجى كتابة سبب الإلغاء أو تأكيد الإلغاء بدون سبب")

    sales = db.query(models.Sale).filter(
        models.Sale.id.in_(payload.ids),
        models.Sale.status == "active"
    ).all()

    found_ids = {s.id for s in sales}
    failed_ids = [i for i in payload.ids if i not in found_ids]
    chassis_numbers = [s.chassis_number for s in sales]

    for sale in sales:
        sale.status = "cancelled"
        sale.cancelled_at = func.now()
        sale.cancel_reason = reason or None
        sale.cancelled_by_id = current_user_id

    db.commit()
    details_parts = []
    if chassis_numbers:
        details_parts.append("الهياكل: " + "، ".join(chassis_numbers))
    if reason:
        details_parts.append(f"السبب: {reason}")
    audit_crud.log_action(
        db, "bulk_cancel", "sale", None, current_user_id,
        entity_label=f"{len(sales)} عملية بيع", details=" | ".join(details_parts) if details_parts else None
    )
    return {
        "success_count": len(sales),
        "failed_ids": failed_ids,
        "message": f"تم إلغاء {len(sales)} عملية بيع"
    }