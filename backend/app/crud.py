from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from . import models, schemas
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from . import workshop_crud

# ====================== WORKERS (تقرير للوحة الإدارة) ======================
def get_workers_with_records(db: Session):
    """
    يرجع كل العمال (الأحدث أولاً) مع ملخص سجلات التجميع الخاصة بكل عامل.
    """
    workers = db.query(models.Worker)\
                .order_by(desc(models.Worker.id))\
                .all()

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
    return result

# ====================== CUSTOMERS ======================
def create_customer(db: Session, customer: schemas.CustomerCreate):
    db_customer = models.Customer(
        name=customer.name,
        phone=customer.phone,
        address=customer.address
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def get_customers_with_sales(db: Session):
    """
    يرجع كل العملاء (الأحدث أولاً) مع تفاصيل مشترياتهم.
    """
    customers = db.query(models.Customer)\
                  .order_by(models.Customer.id.desc())\
                  .all()

    result = []
    for c in customers:
        sales = db.query(models.Sale).filter(models.Sale.customer_id == c.id).all() \
                if hasattr(models.Sale, 'customer_id') else \
                db.query(models.Sale).filter(models.Sale.customer_name == c.name).all()
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
    return result


# ====================== SALES ======================
def create_sale(db: Session, sale: schemas.SaleCreate):
    """تسجيل بيع جديد لعميل موجود مسبقاً (يُحدَّد عبر customer_id)"""
    existing_sale = db.query(models.Sale).filter(
        models.Sale.chassis_number == sale.chassis_number
    ).first()

    if existing_sale:
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
        **({"sale_date": sale.sale_date} if sale.sale_date else {})
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    return db_sale

def get_sales(db: Session, skip: int = 0, limit: int = 50):
    """عرض المبيعات مع تحميل بيانات العميل بطريقة فعالة"""
    sales = db.query(models.Sale)\
              .options(joinedload(models.Sale.customer))\
              .order_by(desc(models.Sale.sale_date))\
              .offset(skip).limit(limit).all()

    # إضافة اسم العميل
    for sale in sales:
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"

    return sales


# ====================== CHASSIS (متاح للبيع) ======================
def get_available_chassis(db: Session):
    """
    يرجع أرقام الهياكل المكتملة التجميع (سواء عبر 'تجميع_كامل'
    أو عبر 'تجميع_الهيكل' + 'توصيل_الكهرباء_والغلاف' معًا)
    ولم تُباع بعد.
    """
    sold_numbers = {s[0] for s in db.query(models.Sale.chassis_number).all()}

    all_records = db.query(models.AssemblyRecord).all()

    # تجميع السجلات حسب رقم الهيكل
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    available = [
        chassis_number
        for chassis_number, records in records_by_chassis.items()
        if workshop_crud.is_chassis_complete(records) and chassis_number not in sold_numbers
    ]

    return sorted(available)


# ====================== CHASSIS (كل الهياكل) ======================
def get_all_chassis_numbers(db: Session):
    """
    يرجع كل أرقام الهياكل التي دخلت النظام (لها سجل تجميع واحد على الأقل)
    بغض النظر عن حالة البيع أو اكتمال التجميع.
    """
    chassis_numbers = (
        db.query(models.AssemblyRecord.chassis_number)
        .distinct()
        .order_by(models.AssemblyRecord.chassis_number)
        .all()
    )
    return [c[0] for c in chassis_numbers]

# ====================== CHASSIS (ملخص شامل للوحة الإدارة) ======================
def get_chassis_summary(db: Session):
    """
    يرجع ملخصًا لكل هيكل دخل النظام: حالة الاكتمال، حالة البيع،
    وعدد الأعطال المعلقة.
    """
    all_records = db.query(models.AssemblyRecord).all()
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    sold_map = {
        s.chassis_number: s
        for s in db.query(models.Sale).options(joinedload(models.Sale.customer)).all()
    }

    all_faults = db.query(models.Fault).all()
    faults_by_chassis = {}
    for f in all_faults:
        faults_by_chassis.setdefault(f.chassis_number, []).append(f)

    summary = []
    for chassis_number, records in records_by_chassis.items():
        is_complete = workshop_crud.is_chassis_complete(records)
        sale = sold_map.get(chassis_number)
        faults = faults_by_chassis.get(chassis_number, [])
        pending_faults = [f for f in faults if f.status == "pending"]

        summary.append({
            "chassis_number": chassis_number,
            "is_complete": is_complete,
            "is_sold": sale is not None,
            "customer_name": sale.customer.name if sale and sale.customer else None,
            "pending_faults_count": len(pending_faults),
            "total_faults_count": len(faults),
            "last_updated": max(r.timestamp for r in records),
        })

    return sorted(summary, key=lambda x: x["chassis_number"])


# ====================== FAULTS ======================
def create_fault(db: Session, fault: schemas.FaultCreate):
    db_fault = models.Fault(
        chassis_number=fault.chassis_number,
        description=fault.description,
        status=fault.status or "pending"
    )
    db.add(db_fault)
    db.commit()
    db.refresh(db_fault)
    return db_fault


def get_faults_by_chassis(db: Session, chassis_number: str):

    faults = (
        db.query(models.Fault)
        .filter(
            models.Fault.chassis_number == chassis_number
        )
        .order_by(
            desc(models.Fault.reported_date)
        )
        .all()
    )

    latest_assembly = (
        db.query(models.AssemblyRecord)
        .filter(
            models.AssemblyRecord.chassis_number == chassis_number
        )
        .order_by(
            desc(models.AssemblyRecord.timestamp)
        )
        .first()
    )

    worker_name = (
        latest_assembly.worker.name
        if latest_assembly and latest_assembly.worker
        else "غير معروف"
    )

    for fault in faults:
        fault.worker_name = worker_name

    return faults


def get_all_faults(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Fault)\
              .order_by(desc(models.Fault.reported_date))\
              .offset(skip).limit(limit).all()


# ====================== DASHBOARD ======================
def get_dashboard_stats(db: Session):
    """إحصائيات لوحة الإدارة - نسخة محسنة وأكثر دقة"""

    all_records = db.query(models.AssemblyRecord).all()

    # تجميع السجلات حسب رقم الهيكل
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    total_chassis = len(records_by_chassis)

    completed = sum(
        1 for records in records_by_chassis.values()
        if workshop_crud.is_chassis_complete(records)
    )

    # عدد المبيعات
    sold = db.query(func.count(models.Sale.id)).scalar() or 0

    # الأعطال المعلقة
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

    # إضافة اسم العامل
    for record in assembly_records:

        if record.worker:
            record.worker_name = record.worker.name

        else:
            record.worker_name = "غير معروف"


    sale = (
        db.query(models.Sale)
        .filter(
            models.Sale.chassis_number == chassis_number
        )
        .first()
    )

    # إضافة اسم العميل
    if sale:

        if sale.customer:
            sale.customer_name = sale.customer.name

        else:
            sale.customer_name = "غير معروف"


    faults = get_faults_by_chassis(
        db,
        chassis_number
    )

    return {
        "chassis_number": chassis_number,
        "assembly_history": assembly_records,
        "sale": sale,
        "faults": faults
    }
