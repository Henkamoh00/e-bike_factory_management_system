from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from . import models, schemas, audit_crud


def create_customer(db: Session, customer: schemas.CustomerCreate, current_user_id: int):
    db_customer = models.Customer(
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        created_by_id=current_user_id,
    )
    db.add(db_customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("العميل موجود مسبقاً")
    db.refresh(db_customer)
    audit_crud.log_action(db, "create", "customer", db_customer.id, current_user_id, entity_label=db_customer.name)
    return db_customer


def update_customer(db: Session, customer_id: int, data: schemas.CustomerUpdate, current_user_id: int | None = None):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise ValueError("العميل غير موجود")
    if customer.is_deleted:
        raise ValueError("لا يمكن تعديل عميل مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        customer.name = data.name
    if data.phone is not None:
        customer.phone = data.phone
    if data.address is not None:
        customer.address = data.address
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد عميل آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(customer)
    audit_crud.log_action(db, "update", "customer", customer.id, current_user_id, entity_label=customer.name)
    return customer


def soft_delete_customer(db: Session, customer_id: int, current_user_id: int):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise ValueError("العميل غير موجود")
    customer.is_deleted = True
    customer.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "customer", customer.id, current_user_id, entity_label=customer.name)
    return customer


def search_customers_simple(db: Session, q: str | None = None, limit: int = 20):
    query = db.query(models.Customer).filter(models.Customer.is_deleted == False)
    if q:
        query = query.filter(models.Customer.name.ilike(f"%{q}%"))
    return query.order_by(models.Customer.name).limit(limit).all()


def get_customers_with_sales(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.Customer).filter(models.Customer.is_deleted == False)
    if search:
        query = query.filter(models.Customer.name.ilike(f"%{search}%"))

    total = query.count()
    customers = query.order_by(models.Customer.id.desc()).offset(skip).limit(limit).all()

    if not customers:
        return [], total

    # 🆕 إصلاح أداء (N+1): جلب كل المبيعات النشطة لعملاء هذه الصفحة بطلب واحد
    # بدل استعلام منفصل لكل عميل داخل الحلقة
    customer_ids = [c.id for c in customers]
    all_sales = db.query(models.Sale).filter(
        models.Sale.customer_id.in_(customer_ids),
        models.Sale.status == "active"
    ).all()

    sales_by_customer = {}
    for s in all_sales:
        sales_by_customer.setdefault(s.customer_id, []).append(s)

    result = []
    for c in customers:
        sales = sales_by_customer.get(c.id, [])
        result.append({
            "id":               c.id,
            "name":             c.name,
            "phone":            c.phone,
            "address":          c.address,
            "total_purchases":  len(sales),
            "sales": [
                {
                    "id":             s.id,
                    "chassis_number": s.chassis_number,
                    "sale_date":      s.sale_date,
                }
                for s in sales
            ],
        })
    return result, total


def get_archived_customers(db: Session, skip: int = 0, limit: int = 20):
    query = db.query(models.Customer)\
              .options(joinedload(models.Customer.deleted_by))\
              .filter(models.Customer.is_deleted == True)\
              .order_by(desc(models.Customer.id))
    total = query.count()
    customers = query.offset(skip).limit(limit).all()
    for c in customers:
        c.deleted_by_username = c.deleted_by.username if c.deleted_by else None
    return customers, total


def restore_customer(db: Session, customer_id: int, current_user_id: int):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise ValueError("العميل غير موجود")
    if not customer.is_deleted:
        raise ValueError("العميل غير مؤرشف أصلاً")

    duplicate = db.query(models.Customer).filter(
        models.Customer.name == customer.name,
        models.Customer.is_deleted == False,
        models.Customer.id != customer.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة العميل، يوجد عميل نشط حاليًا بنفس الاسم '{customer.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    customer.is_deleted = False
    customer.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"لا يمكن استعادة العميل، يوجد عميل نشط حاليًا بنفس الاسم '{customer.name}'")
    audit_crud.log_action(db, "restore", "customer", customer.id, current_user_id, entity_label=customer.name)
    return customer


def bulk_soft_delete_customers(db: Session, ids: list[int], current_user_id: int):
    customers = db.query(models.Customer).filter(models.Customer.id.in_(ids)).all()
    found_ids = {c.id for c in customers}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [c.name for c in customers]
    for c in customers:
        c.is_deleted = True
        c.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(
        db, "bulk_delete", "customer", None, current_user_id,
        entity_label=f"{len(customers)} عميل", details="، ".join(names) if names else None
    )
    return {"success_count": len(customers), "failed_ids": failed_ids, "message": f"تم حذف {len(customers)} عميل"}