from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from fastapi import HTTPException
from . import models, schemas


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


# ====================== ASSEMBLY STAGES ======================
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

def is_chassis_complete(records: list) -> bool:
    stages = {r.stage for r in records}
    return (
        STAGE_COMPLETE in stages
        or (STAGE_ASSEMBLY in stages and STAGE_COVER in stages)
    )


# ====================== ASSEMBLY RECORDS ======================
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

    if is_chassis_complete(all_records):
        raise HTTPException(
            status_code=409,
            detail=f"🚫 الهيكل رقم ({assembly.chassis_number}) مكتمل مسبقاً. لا يمكن إضافة أي سجل جديد."
        )

    if stage == STAGE_COVER and STAGE_ASSEMBLY not in existing_stages:
        raise HTTPException(
            status_code=422,
            detail=f"⛔ لا يمكن تسجيل '{_label(STAGE_COVER)}' قبل '{_label(STAGE_ASSEMBLY)}'."
        )

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

        rec = same_stage_records[0]
        rec.worker_id = worker.id
        rec.timestamp = func.now()
        db.commit()
        db.refresh(rec)
        return rec

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