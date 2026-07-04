from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from . import models, schemas
from fastapi import HTTPException
from sqlalchemy.orm import joinedload


# ====================== WORKERS ======================
def get_or_create_worker(db: Session, name: str):
    worker = db.query(models.Worker).filter(models.Worker.name == name).first()
    if not worker:
        worker = models.Worker(name=name)
        db.add(worker)
        db.commit()
        db.refresh(worker)
    return worker


def get_workers(db: Session):
    return db.query(models.Worker).order_by(models.Worker.name).all()


# ====================== ASSEMBLY RECORDS ======================

STAGE_LABELS = {
    "تجميع_الهيكل": "تجميع الهيكل",
    "توصيل_الكهرباء_والغلاف": "توصيل الكهرباء والغلاف",
    "تجميع_كامل": "تجميع كامل",
}

STAGE_ASSEMBLY = "تجميع_الهيكل"
STAGE_COVER    = "توصيل_الكهرباء_والغلاف"
STAGE_COMPLETE = "تجميع_كامل"

def _label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage)

def _is_chassis_complete(records: list) -> bool:
    stages = {r.stage for r in records}
    return (
        STAGE_COMPLETE in stages
        or (STAGE_ASSEMBLY in stages and STAGE_COVER in stages)
    )


def create_assembly_record(
    db: Session,
    assembly: schemas.AssemblyCreate,
    force: bool = False,
):
    stage = assembly.stage.value if hasattr(assembly.stage, 'value') else assembly.stage
    worker = get_or_create_worker(db, assembly.worker_name)

    all_records = db.query(models.AssemblyRecord)\
        .filter(models.AssemblyRecord.chassis_number == assembly.chassis_number)\
        .all()

    existing_stages = {r.stage for r in all_records}

    # ... (الكود الأصلي الخاص بك كاملاً دون تغيير) ...
    if STAGE_COMPLETE in existing_stages and stage != STAGE_COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"🚫 الهيكل ({assembly.chassis_number}) مسجَّل بمرحلة '{_label(STAGE_COMPLETE)}' — لا يمكن إضافة أي مرحلة أخرى."
        )

    if stage == STAGE_COMPLETE and STAGE_ASSEMBLY in existing_stages:
        raise HTTPException(
            status_code=409,
            detail=f"🚫 الهيكل ({assembly.chassis_number}) يمتلك سجل '{_label(STAGE_ASSEMBLY)}' مسبقاً."
        )

    if _is_chassis_complete(all_records):
        raise HTTPException(
            status_code=409,
            detail=f"🚫 الهيكل رقم ({assembly.chassis_number}) مكتمل مسبقاً. لا يمكن إضافة أي سجل جديد."
        )

    if stage == STAGE_COVER and STAGE_ASSEMBLY not in existing_stages:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ لا يمكن تسجيل '{_label(STAGE_COVER)}' قبل '{_label(STAGE_ASSEMBLY)}'."
        )

    # باقي المنطق الأصلي الخاص بك...
    same_stage_records = [r for r in all_records if r.stage == stage]

    if same_stage_records:
        same_stage_same_worker = [r for r in same_stage_records if r.worker_id == worker.id]
        if same_stage_same_worker:
            rec = same_stage_same_worker[0]
            rec.timestamp = func.now()
            db.commit()
            db.refresh(rec)
            return rec

        if not force:
            existing_worker_name = same_stage_records[0].worker.name if same_stage_records[0].worker else "غير معروف"
            raise HTTPException(
                status_code=409,
                detail=f"⚠️ مرحلة '{_label(stage)}' للهيكل ({assembly.chassis_number}) سبق أن قام بها '{existing_worker_name}'. هل أنت متأكد من تسجيلها باسم '{assembly.worker_name}'؟",
                headers={"X-Confirm-Required": "true"},
            )

        # Force update
        rec = same_stage_records[0]
        rec.worker_id = worker.id
        rec.timestamp = func.now()
        db.commit()
        db.refresh(rec)
        return rec

    # سجل جديد
    record = models.AssemblyRecord(
        chassis_number=assembly.chassis_number,
        worker_id=worker.id,
        stage=stage,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_assembly_records(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.AssemblyRecord)\
              .order_by(desc(models.AssemblyRecord.timestamp))\
              .offset(skip).limit(limit).all()


def get_assembly_by_chassis(db: Session, chassis_number: str):
    return db.query(models.AssemblyRecord)\
              .filter(models.AssemblyRecord.chassis_number == chassis_number)\
              .order_by(models.AssemblyRecord.timestamp).all()


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


def get_customers(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.Customer).offset(skip).limit(limit).all()


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
    يرجع أرقام الهياكل المكتملة التجميع (لها مرحلة 'تجميع_كامل')
    ولم تُباع بعد.
    """
    sold_subquery = db.query(models.Sale.chassis_number).subquery()

    chassis_numbers = (
        db.query(models.AssemblyRecord.chassis_number)
        .filter(models.AssemblyRecord.stage == models.AssemblyStage.FINAL_ASSEMBLY)
        .filter(models.AssemblyRecord.chassis_number.notin_(sold_subquery))
        .distinct()
        .order_by(models.AssemblyRecord.chassis_number)
        .all()
    )
    return [c[0] for c in chassis_numbers]


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
    
    # إجمالي الهياكل الفريدة
    total_chassis = db.query(func.count(models.AssemblyRecord.chassis_number.distinct())).scalar() or 0
    
    # الدراجات المكتملة (لها مرحلة التجميع الكامل)
    completed = db.query(func.count(models.AssemblyRecord.chassis_number.distinct())).filter(
        models.AssemblyRecord.stage == models.AssemblyStage.FINAL_ASSEMBLY
    ).scalar() or 0
    
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

    assembly_records = get_assembly_by_chassis(
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


# ====================== إضافات جديدة للإدارة ======================
def get_all_assemblies(db: Session, skip: int = 0, limit: int = 100):
    """عرض كل عمليات التجميع (للوحة الإدارة)"""
    return get_assembly_records(db, skip, limit)


# ====================== دوال إضافية للوحة الإدارة ======================

def get_total_assemblies(db: Session):
    """عدد كل عمليات التجميع"""
    return db.query(models.AssemblyRecord).count()


def get_completed_chassis(db: Session):
    """عدد الدراجات المكتملة"""
    return db.query(models.AssemblyRecord).filter(
        models.AssemblyRecord.stage == models.AssemblyStage.FINAL_ASSEMBLY
    ).distinct(models.AssemblyRecord.chassis_number).count()


def get_pending_faults(db: Session):
    """عدد الأعطال المعلقة"""
    return db.query(models.Fault).filter(
        models.Fault.status == "pending"
    ).count()