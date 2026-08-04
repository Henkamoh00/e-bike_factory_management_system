from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from . import models, schemas, workshop_crud, audit_crud
from fastapi import HTTPException
from sqlalchemy.orm import joinedload

# ====================== WORKERS (تقرير للوحة الإدارة) ======================
def get_workers_with_records(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.Worker).filter(models.Worker.is_deleted == False)
    if search:
        query = query.filter(models.Worker.name.ilike(f"%{search}%"))

    total = query.count()
    workers = query.order_by(desc(models.Worker.id)).offset(skip).limit(limit).all()

    result = []
    for w in workers:
        records = db.query(models.AssemblyRecord).filter(
            models.AssemblyRecord.worker_id == w.id
        ).all()
        stages_summary = {}
        for r in records:
            stage_val = r.stage.value if hasattr(r.stage, 'value') else r.stage
            stages_summary[stage_val] = stages_summary.get(stage_val, 0) + 1
        result.append({
            "id":             w.id,
            "name":           w.name,
            "phone":          getattr(w, 'phone', None),
            "total_records":  len(records),
            "stages_summary": stages_summary,
            "records": [
                {
                    "id":             r.id,
                    "chassis_number": r.chassis_number,
                    "stage":          r.stage.value if hasattr(r.stage, 'value') else r.stage,
                    "timestamp":      r.timestamp,
                }
                for r in records
            ],
        })
    return result, total

# ====================== CUSTOMERS ======================
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

    result = []
    for c in customers:
        sales = db.query(models.Sale).filter(
            models.Sale.customer_id == c.id,
            models.Sale.status == "active"
        ).all()
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


# ====================== BULK: WORKERS / CUSTOMERS ======================
def bulk_soft_delete_workers(db: Session, ids: List[int], current_user_id: int):
    workers = db.query(models.Worker).filter(models.Worker.id.in_(ids)).all()
    found_ids = {w.id for w in workers}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [w.name for w in workers]
    for w in workers:
        w.is_deleted = True
        w.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(
        db, "bulk_delete", "worker", None, current_user_id,
        entity_label=f"{len(workers)} عامل", details="، ".join(names) if names else None
    )
    return {"success_count": len(workers), "failed_ids": failed_ids, "message": f"تم حذف {len(workers)} عامل"}


def bulk_soft_delete_customers(db: Session, ids: List[int], current_user_id: int):
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


# ====================== SALES ======================
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


# ====================== BULK: SALES ======================
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


# ====================== CHASSIS (متاح للبيع) ======================
def get_available_chassis(db: Session):
    sold_numbers = {
        s[0] for s in db.query(models.Sale.chassis_number)
        .filter(models.Sale.status == "active")
        .all()
    }

    faulty_numbers = {
        f[0] for f in db.query(models.Fault.chassis_number)
        .filter(models.Fault.status == "pending")
        .distinct()
        .all()
    }

    all_records = db.query(models.AssemblyRecord).all()

    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    available = [
        chassis_number
        for chassis_number, records in records_by_chassis.items()
        if workshop_crud.is_chassis_complete(records)
        and chassis_number not in sold_numbers
        and chassis_number not in faulty_numbers
    ]

    return sorted(available)


# ====================== CHASSIS (كل الهياكل) ======================
def get_all_chassis_numbers(db: Session):
    chassis_numbers = (
        db.query(models.AssemblyRecord.chassis_number)
        .distinct()
        .order_by(models.AssemblyRecord.chassis_number)
        .all()
    )
    return [c[0] for c in chassis_numbers]

# ====================== CHASSIS (ملخص شامل للوحة الإدارة - مُصفَّح ومُفلتَر) ======================
def get_chassis_summary(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    chassis_number: str | None = None,
    status: str | None = None,
    worker_name: str | None = None,
    stage: str | None = None,
    bike_type: str | None = None,
    bike_color: str | None = None,
):
    """
    🆕 مُصفَّحة ومُفلتَرة من جهة السيرفر الآن.
    ملاحظة: البيانات مُجمَّعة (aggregated) من سجلات التجميع، لذا يتم بناء
    الملخص الكامل أولاً بالذاكرة ثم تُطبَّق الفلاتر والتصفيح على النتيجة،
    لأن التجميع (حسب رقم الهيكل) لا يمكن أن يتم مباشرة عبر offset/limit في SQL
    بسبب طبيعة العلاقة (سجل واحد أو أكثر لكل هيكل).
    """
    all_records = db.query(models.AssemblyRecord).all()
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    active_sold_map = {
        s.chassis_number: s
        for s in db.query(models.Sale)
        .options(joinedload(models.Sale.customer))
        .filter(models.Sale.status == "active")
        .all()
    }

    all_faults = db.query(models.Fault).all()
    faults_by_chassis = {}
    for f in all_faults:
        faults_by_chassis.setdefault(f.chassis_number, []).append(f)

    summary = []
    for chassis_num, records in records_by_chassis.items():
        is_complete = workshop_crud.is_chassis_complete(records)
        sale = active_sold_map.get(chassis_num)
        faults = faults_by_chassis.get(chassis_num, [])
        pending_faults = [f for f in faults if f.status == "pending"]

        worker_names = list({r.worker.name for r in records if r.worker})
        stage_values = list({r.stage.value if hasattr(r.stage, 'value') else r.stage for r in records})
        bike_type_name = next((r.bike_type.name for r in records if r.bike_type), None)
        bike_color_name = next((r.bike_color.name for r in records if r.bike_color), None)

        stage_workers = {
            (r.stage.value if hasattr(r.stage, 'value') else r.stage): (r.worker.name if r.worker else None)
            for r in records
        }

        summary.append({
            "chassis_number": chassis_num,
            "is_complete": is_complete,
            "is_sold": sale is not None,
            "workers": worker_names,
            "stages": stage_values,
            "stage_workers": stage_workers,
            "bike_type": bike_type_name,
            "bike_color": bike_color_name,
            "customer_name": sale.customer.name if sale and sale.customer else None,
            "pending_faults_count": len(pending_faults),
            "total_faults_count": len(faults),
            "last_updated": max(r.timestamp for r in records),
        })

    # ── تطبيق الفلاتر (بنفس منطق الفرونت إند القديم) ──────────────────
    def matches(item):
        if chassis_number and chassis_number.lower() not in item["chassis_number"].lower():
            return False
        if status == "available" and (not item["is_complete"] or item["is_sold"]):
            return False
        if status == "sold" and not item["is_sold"]:
            return False
        if status == "in_progress" and item["is_complete"]:
            return False
        if status == "has_fault" and item["pending_faults_count"] == 0:
            return False

        stage_workers = item["stage_workers"]
        if worker_name and stage:
            direct_match = stage_workers.get(stage) == worker_name
            covered_by_full = (
                stage in (workshop_crud.STAGE_ASSEMBLY, workshop_crud.STAGE_COVER)
                and stage_workers.get(workshop_crud.STAGE_COMPLETE) == worker_name
            )
            if not direct_match and not covered_by_full:
                return False
        elif worker_name:
            if worker_name not in item["workers"]:
                return False
        elif stage:
            if stage not in item["stages"]:
                return False

        if bike_type and item["bike_type"] != bike_type:
            return False
        if bike_color and item["bike_color"] != bike_color:
            return False
        return True

    filtered = [s for s in summary if matches(s)]
    filtered.sort(key=lambda x: x["chassis_number"])

    total = len(filtered)
    paginated = filtered[skip:skip + limit]
    return paginated, total


# ====================== FAULTS ======================
def create_fault(db: Session, fault: schemas.FaultCreate, current_user_id: int):
    db_fault = models.Fault(
        chassis_number=fault.chassis_number,
        description=fault.description,
        related_stage=fault.related_stage,
        status=fault.status or "pending",
        reported_by_id=current_user_id,
    )
    db.add(db_fault)
    db.commit()
    db.refresh(db_fault)
    audit_crud.log_action(db, "create", "fault", db_fault.id, current_user_id, entity_label=db_fault.chassis_number)
    return db_fault


def cancel_fault(db: Session, fault_id: int, payload: schemas.FaultCancel, current_user_id: int):
    fault = db.query(models.Fault).filter(models.Fault.id == fault_id).first()
    if not fault:
        raise ValueError("العطل غير موجود")
    if fault.status == "fixed":
        raise ValueError("لا يمكن إلغاء عطل تم إصلاحه مسبقاً")
    if fault.status == "cancelled":
        raise ValueError("العطل ملغى مسبقاً")

    reason = (payload.reason or "").strip()
    if not reason and not payload.confirm_no_reason:
        raise ValueError("يرجى كتابة سبب الإلغاء أو تأكيد الإلغاء بدون سبب")

    fault.status = "cancelled"
    fault.resolved_at = func.now()
    fault.cancel_reason = reason or None
    fault.cancelled_by_id = current_user_id
    db.commit()
    db.refresh(fault)
    audit_crud.log_action(
        db, "cancel", "fault", fault.id, current_user_id,
        entity_label=fault.chassis_number, details=fault.cancel_reason
    )
    return fault


def _attach_fault_extras(db: Session, faults):
    for fault in faults:
        for repair in fault.repairs:
            repair.worker_name = repair.worker.name if repair.worker else "غير معروف"
            repair.recorded_by_username = repair.recorded_by.username if repair.recorded_by else None

        fault.reported_by_username = fault.reported_by.username if fault.reported_by else None
        fault.cancelled_by_username = fault.cancelled_by.username if fault.cancelled_by else None

        fault.responsible_worker_name = None
        if fault.related_stage:
            record = (
                db.query(models.AssemblyRecord)
                .filter(
                    models.AssemblyRecord.chassis_number == fault.chassis_number,
                    models.AssemblyRecord.stage == fault.related_stage
                )
                .first()
            )
            if not record:
                record = (
                    db.query(models.AssemblyRecord)
                    .filter(
                        models.AssemblyRecord.chassis_number == fault.chassis_number,
                        models.AssemblyRecord.stage == workshop_crud.STAGE_COMPLETE
                    )
                    .first()
                )
            if record and record.worker:
                fault.responsible_worker_name = record.worker.name
    return faults

def get_faults_by_chassis(db: Session, chassis_number: str):
    faults = (
        db.query(models.Fault)
        .filter(models.Fault.chassis_number == chassis_number)
        .order_by(desc(models.Fault.reported_date))
        .all()
    )
    return _attach_fault_extras(db, faults)


def get_all_faults(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    chassis_number: str | None = None,
    status: str | None = None,
    repaired_by: str | None = None,
    responsible_worker: str | None = None,
):
    """🆕 مُصفَّحة ومُفلتَرة من جهة السيرفر"""
    query = db.query(models.Fault)

    if chassis_number:
        query = query.filter(models.Fault.chassis_number.ilike(f"%{chassis_number}%"))
    if status:
        query = query.filter(models.Fault.status == status)

    total_query_ids = [f.id for f in query.with_entities(models.Fault.id).all()]

    faults = query.order_by(desc(models.Fault.reported_date)).all()
    faults = _attach_fault_extras(db, faults)

    if repaired_by:
        faults = [f for f in faults if any(r.worker_name == repaired_by for r in f.repairs)]
    if responsible_worker:
        faults = [f for f in faults if f.responsible_worker_name == responsible_worker]

    total = len(faults)
    paginated = faults[skip:skip + limit]
    return paginated, total


def create_fault_repair(db: Session, fault_id: int, repair: schemas.FaultRepairCreate, current_user_id: int):
    db_fault = db.query(models.Fault).filter(models.Fault.id == fault_id).first()
    if not db_fault:
        raise ValueError("العطل غير موجود")
    if db_fault.status == "fixed":
        raise ValueError("هذا العطل مسجل مسبقاً كمُصلَح")
    if db_fault.status == "cancelled":
        raise ValueError("هذا العطل ملغى، لا يمكن تسجيل تصليح له")

    worker = workshop_crud.get_or_create_worker(db, repair.worker_name, current_user_id)

    db_repair = models.FaultRepair(
        fault_id=fault_id,
        worker_id=worker.id,
        notes=repair.notes,
        recorded_by_id=current_user_id,
    )
    db.add(db_repair)

    db_fault.status = "fixed"
    db_fault.resolved_at = func.now()

    db.commit()
    db.refresh(db_repair)
    db_repair.worker_name = worker.name
    audit_crud.log_action(
        db, "repair", "fault", db_fault.id, current_user_id,
        entity_label=f"{db_fault.chassis_number} — بواسطة {worker.name}"
    )
    return db_repair


def get_suggested_worker_for_fault(db: Session, fault_id: int):
    db_fault = db.query(models.Fault).filter(models.Fault.id == fault_id).first()
    if not db_fault or not db_fault.related_stage:
        return None

    record = (
        db.query(models.AssemblyRecord)
        .filter(
            models.AssemblyRecord.chassis_number == db_fault.chassis_number,
            models.AssemblyRecord.stage == db_fault.related_stage
        )
        .first()
    )
    if record and record.worker:
        return {"worker_id": record.worker.id, "worker_name": record.worker.name}
    return None


# ====================== BULK: FAULTS ======================
def bulk_cancel_faults(db: Session, payload: schemas.BulkCancel, current_user_id: int):
    reason = (payload.reason or "").strip()
    if not reason and not payload.confirm_no_reason:
        raise ValueError("يرجى كتابة سبب الإلغاء أو تأكيد الإلغاء بدون سبب")

    faults = db.query(models.Fault).filter(
        models.Fault.id.in_(payload.ids),
        models.Fault.status == "pending"
    ).all()

    found_ids = {f.id for f in faults}
    failed_ids = [i for i in payload.ids if i not in found_ids]
    chassis_numbers = [f.chassis_number for f in faults]

    for fault in faults:
        fault.status = "cancelled"
        fault.resolved_at = func.now()
        fault.cancel_reason = reason or None
        fault.cancelled_by_id = current_user_id

    db.commit()
    details_parts = []
    if chassis_numbers:
        details_parts.append("الهياكل: " + "، ".join(chassis_numbers))
    if reason:
        details_parts.append(f"السبب: {reason}")
    audit_crud.log_action(
        db, "bulk_cancel", "fault", None, current_user_id,
        entity_label=f"{len(faults)} عطل", details=" | ".join(details_parts) if details_parts else None
    )
    return {
        "success_count": len(faults),
        "failed_ids": failed_ids,
        "message": f"تم إلغاء {len(faults)} عطل"
    }


def bulk_mark_faults_fixed(db: Session, ids: List[int], worker_name: str, current_user_id: int):
    worker = workshop_crud.get_or_create_worker(db, worker_name, current_user_id)
    faults = db.query(models.Fault).filter(
        models.Fault.id.in_(ids),
        models.Fault.status == "pending"
    ).all()

    found_ids = {f.id for f in faults}
    failed_ids = [i for i in ids if i not in found_ids]
    chassis_numbers = [f.chassis_number for f in faults]

    for fault in faults:
        repair = models.FaultRepair(fault_id=fault.id, worker_id=worker.id, recorded_by_id=current_user_id)
        db.add(repair)
        fault.status = "fixed"
        fault.resolved_at = func.now()

    db.commit()
    audit_crud.log_action(
        db, "bulk_repair", "fault", None, current_user_id,
        entity_label=f"{len(faults)} عطل بواسطة {worker_name}",
        details="الهياكل: " + "، ".join(chassis_numbers) if chassis_numbers else None
    )
    return {
        "success_count": len(faults),
        "failed_ids": failed_ids,
        "message": f"تم إصلاح {len(faults)} عطل بواسطة {worker_name}"
    }


# ====================== DASHBOARD ======================
def get_dashboard_stats(db: Session):
    all_records = db.query(models.AssemblyRecord).all()

    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    total_chassis = len(records_by_chassis)

    completed = sum(
        1 for records in records_by_chassis.values()
        if workshop_crud.is_chassis_complete(records)
    )

    sold = db.query(func.count(models.Sale.id)).filter(
        models.Sale.status == "active"
    ).scalar() or 0

    pending_faults = db.query(func.count(models.Fault.id)).filter(
        models.Fault.status == "pending"
    ).scalar() or 0

    return {
        "total_chassis": total_chassis,
        "completed": completed,
        "in_progress": total_chassis - completed,
        "sold": sold,
        "pending_faults": pending_faults
    }


def get_full_chassis_history(db: Session, chassis_number: str):

    assembly_records = workshop_crud.get_assembly_by_chassis(
        db,
        chassis_number
    )

    for record in assembly_records:
        if record.worker:
            record.worker_name = record.worker.name
        else:
            record.worker_name = "غير معروف"

    sales = (
        db.query(models.Sale)
        .filter(
            models.Sale.chassis_number == chassis_number
        )
        .order_by(desc(models.Sale.sale_date))
        .all()
    )

    for sale in sales:
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"

    faults = get_faults_by_chassis(
        db,
        chassis_number
    )

    bike_type_name = next((r.bike_type.name for r in assembly_records if r.bike_type), None)
    bike_color_name = next((r.bike_color.name for r in assembly_records if r.bike_color), None)

    return {
        "chassis_number": chassis_number,
        "assembly_history": assembly_records,
        "sales": sales,
        "faults": faults,
        "bike_type": bike_type_name,
        "bike_color": bike_color_name,
    }


# ====================== BIKE TYPES / COLORS (تقرير للوحة الإدارة) ======================
def get_bike_types_with_usage(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.BikeType).filter(models.BikeType.is_deleted == False)
    if search:
        query = query.filter(models.BikeType.name.ilike(f"%{search}%"))

    total = query.count()
    types = query.order_by(desc(models.BikeType.id)).offset(skip).limit(limit).all()

    result = []
    for t in types:
        count = db.query(func.count(models.AssemblyRecord.id))\
                   .filter(models.AssemblyRecord.bike_type_id == t.id).scalar() or 0
        result.append({"id": t.id, "name": t.name, "usage_count": count})
    return result, total


def get_bike_colors_with_usage(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.BikeColor).filter(models.BikeColor.is_deleted == False)
    if search:
        query = query.filter(models.BikeColor.name.ilike(f"%{search}%"))

    total = query.count()
    colors = query.order_by(desc(models.BikeColor.id)).offset(skip).limit(limit).all()

    result = []
    for c in colors:
        count = db.query(func.count(models.AssemblyRecord.id))\
                   .filter(models.AssemblyRecord.bike_color_id == c.id).scalar() or 0
        result.append({"id": c.id, "name": c.name, "usage_count": count})
    return result, total


# ====================== BULK: BIKE TYPES / COLORS ======================
def bulk_soft_delete_bike_types(db: Session, ids: List[int], current_user_id: int):
    types = db.query(models.BikeType).filter(models.BikeType.id.in_(ids)).all()
    found_ids = {t.id for t in types}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [t.name for t in types]
    for t in types:
        t.is_deleted = True
        t.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(
        db, "bulk_delete", "bike_type", None, current_user_id,
        entity_label=f"{len(types)} نوع", details="، ".join(names) if names else None
    )
    return {"success_count": len(types), "failed_ids": failed_ids, "message": f"تم حذف {len(types)} نوع"}


def bulk_soft_delete_bike_colors(db: Session, ids: List[int], current_user_id: int):
    colors = db.query(models.BikeColor).filter(models.BikeColor.id.in_(ids)).all()
    found_ids = {c.id for c in colors}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [c.name for c in colors]
    for c in colors:
        c.is_deleted = True
        c.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(
        db, "bulk_delete", "bike_color", None, current_user_id,
        entity_label=f"{len(colors)} لون", details="، ".join(names) if names else None
    )
    return {"success_count": len(colors), "failed_ids": failed_ids, "message": f"تم حذف {len(colors)} لون"}