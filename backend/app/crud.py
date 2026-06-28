from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from . import models, schemas
from fastapi import HTTPException


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
    "تجميع_الهيكل":              "تجميع الهيكل",
    "توصيل_الكهرباء_والغلاف":    "توصيل الكهرباء والغلاف",
    "تجميع_كامل":                "تجميع كامل",
}

STAGE_ASSEMBLY = "تجميع_الهيكل"
STAGE_COVER    = "توصيل_الكهرباء_والغلاف"
STAGE_COMPLETE = "تجميع_كامل"

def _label(stage: str) -> str:
    """يرجع النص المقروء لقيمة المرحلة."""
    return STAGE_LABELS.get(stage, stage)
 
def _is_chassis_complete(records: list) -> bool:
    """
    الهيكل مكتمل إذا:
      - يوجد سجل 'تركيب كامل'، أو
      - يوجد سجل 'تجميع هيكل' + سجل 'تركيب غلاف' معاً
    """
    stages = {r.stage for r in records}
    return (
        STAGE_COMPLETE in stages
        or (STAGE_ASSEMBLY in stages and STAGE_COVER in stages)
    )
 
 
def create_assembly_record(
    db: Session,
    assembly: schemas.AssemblyCreate,
    force: bool = False,          # لتجاوز تحذير العامل المختلف بعد تأكيد المسؤول
):
    stage = assembly.stage.value if hasattr(assembly.stage, 'value') else assembly.stage
    
    worker = get_or_create_worker(db, assembly.worker_name)
 
    # ── جلب جميع سجلات هذا الهيكل مرة واحدة ──────────────────────────────
    all_records: list[models.AssemblyRecord] = (
        db.query(models.AssemblyRecord)
        .filter(models.AssemblyRecord.chassis_number == assembly.chassis_number)
        .all()
    )
 
    existing_stages = {r.stage for r in all_records}
 
    # ══════════════════════════════════════════════════════════════════════
    # 0. هل الهيكل مكتمل مسبقاً؟  ← لا يُقبل أي سجل جديد
    # ══════════════════════════════════════════════════════════════════════

    # ── أ. تعارض المراحل ───────────────
    #
    if STAGE_COMPLETE in existing_stages and stage != STAGE_COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=(
                f"🚫 الهيكل ({assembly.chassis_number}) مسجَّل بمرحلة "
                f"'{_label(STAGE_COMPLETE)}' — لا يمكن إضافة أي مرحلة أخرى له."
            ),
        )
 
    if stage == STAGE_COMPLETE and STAGE_ASSEMBLY in existing_stages:
        raise HTTPException(
            status_code=409,
            detail=(
                f"🚫 الهيكل ({assembly.chassis_number}) يمتلك سجل "
                f"'{_label(STAGE_ASSEMBLY)}' مسبقاً. "
                f"لا يمكن تسجيل '{_label(STAGE_COMPLETE)}' — "
                f"سجِّل '{_label(STAGE_COVER)}' لإكماله."
            ),
        )
    
    # ── هل الهيكل مكتمل مسبقاً؟ ────────────────
    if _is_chassis_complete(all_records):
        raise HTTPException(
            status_code=409,
            detail=(
                f"🚫 الهيكل رقم ({assembly.chassis_number}) مكتمل مسبقاً. "
                "لا يمكن إضافة أي سجل جديد له."
            ),
        )
 
    # ══════════════════════════════════════════════════════════════════════
    # 1. قواعد خاصة بمرحلة 'تركيب غلاف'
    # ══════════════════════════════════════════════════════════════════════
    if stage == STAGE_COVER:
        if STAGE_ASSEMBLY not in existing_stages:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"⛔ لا يمكن تسجيل '{_label(STAGE_COVER)}' للهيكل ({assembly.chassis_number}) "
                    f"لأنه لم يُسجَّل له '{_label(STAGE_ASSEMBLY)}' بعد. "
                    "يرجى تسجيل مرحلة التجميع أولاً."
                ),
            )
 
    # ══════════════════════════════════════════════════════════════════════
    # 2. البحث عن سجل بنفس الهيكل + نفس المرحلة
    # ══════════════════════════════════════════════════════════════════════
    same_stage_records = [r for r in all_records if r.stage == stage]
 
    if same_stage_records:
        same_stage_same_worker = [
            r for r in same_stage_records if r.worker_id == worker.id
        ]
 
        # ── أ: نفس الهيكل + نفس المرحلة + نفس العامل ──────────────────
        if same_stage_same_worker:
            rec = same_stage_same_worker[0]
            rec.timestamp = func.now()
            db.commit()
            db.refresh(rec)
            # إضافة حقل رسالة مؤقت ليُعاد إرساله للـ API
            rec._info = (
                f"ℹ️ تم تحديث وقت السجل فقط — الهيكل ({assembly.chassis_number}) "
                f"في مرحلة '{_label(stage)}' للعامل '{assembly.worker_name}' "
                "موجود مسبقاً."
            )
            return rec
 
        # ── ب: نفس الهيكل + نفس المرحلة + عامل مختلف ──────────────────
        if not force:
            existing_worker_name = same_stage_records[0].worker.name  # العامل الأصلي
            raise HTTPException(
                status_code=409,
               detail=(
                    f"⚠️ تحذير: مرحلة '{_label(stage)}' "
                    f"للهيكل ({assembly.chassis_number}) "
                    f"سبق أن قام بها العامل '{existing_worker_name}'. "
                    f"هل أنت متأكد من تسجيلها باسم العامل '{assembly.worker_name}'؟"
                ),
                headers={"X-Confirm-Required": "true"},
            )

        # force=True: المسؤول أكّد → حدّث العامل والوقت في السجل الموجود
        rec = same_stage_records[0]
        rec.worker_id = worker.id
        rec.timestamp = func.now()
        db.commit()
        db.refresh(rec)
        return rec  # ← يوقف الدالة هنا، لا يصل لقسم "سجل جديد" أدناه
 
    # ══════════════════════════════════════════════════════════════════════
    # 4. نفس الهيكل + مرحلة مختلفة + نفس العامل  → سجل جديد  ✔
    # 5. نفس الهيكل + مرحلة مختلفة + عامل مختلف → سجل جديد  ✔
    # 6. هيكل مختلف (أي حالة)                    → سجل جديد  ✔
    # ══════════════════════════════════════════════════════════════════════
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
    """الحصول على كل سجلات التجميع لدراجة معينة"""
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
    # التحقق من وجود الدراجة
    existing_sale = db.query(models.Sale).filter(
        models.Sale.chassis_number == sale.chassis_number
    ).first()

    if existing_sale:
        raise ValueError("هذه الدراجة تم بيعها مسبقاً")

    customer = create_customer(db, sale.customer) if not sale.customer_id else None

    db_sale = models.Sale(
        chassis_number=sale.chassis_number,
        customer_id=customer.id if customer else sale.customer_id,
        notes=sale.notes
    )
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    return db_sale


def get_sales(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.Sale)\
              .order_by(desc(models.Sale.sale_date))\
              .offset(skip).limit(limit).all()


# ====================== FAULTS ======================
def create_fault(db: Session, fault: schemas.FaultCreate):
    db_fault = models.Fault(
        chassis_number=fault.chassis_number,
        description=fault.description,
        status=fault.status
    )
    db.add(db_fault)
    db.commit()
    db.refresh(db_fault)
    return db_fault


def get_faults_by_chassis(db: Session, chassis_number: str):
    return db.query(models.Fault)\
              .filter(models.Fault.chassis_number == chassis_number)\
              .order_by(desc(models.Fault.reported_date)).all()


def get_all_faults(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Fault)\
              .order_by(desc(models.Fault.reported_date))\
              .offset(skip).limit(limit).all()


# ====================== DASHBOARD & TRACEABILITY ======================
def get_dashboard_stats(db: Session):
    total_chassis = db.query(func.count(models.AssemblyRecord.chassis_number.distinct())).scalar() or 0
    completed = db.query(func.count(models.AssemblyRecord.id)).filter(
        models.AssemblyRecord.stage == models.AssemblyStage.FINAL_ASSEMBLY
    ).scalar() or 0
    sold = db.query(func.count(models.Sale.id)).scalar() or 0
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
    """الحصول على التاريخ الكامل لدراجة معينة (تجميع + بيع + أعطال)"""
    assembly = get_assembly_by_chassis(db, chassis_number)
    sale = db.query(models.Sale).filter(models.Sale.chassis_number == chassis_number).first()
    faults = get_faults_by_chassis(db, chassis_number)

    return {
        "chassis_number": chassis_number,
        "assembly_history": assembly,
        "sale": sale,
        "faults": faults
    }