from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from . import models, schemas, audit_crud


# ====================== WORKERS ======================
def get_or_create_worker(db: Session, name: str, current_user_id: int | None = None):
    worker = db.query(models.Worker).filter(models.Worker.name == name).first()
    if not worker:
        worker = models.Worker(name=name, created_by_id=current_user_id)
        db.add(worker)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # 🛡️ شبكة أمان لحالات التزامن النادرة (سباق بين طلبين متزامنين بنفس الاسم)
            worker = db.query(models.Worker).filter(models.Worker.name == name).first()
            if not worker:
                raise ValueError("تعذر إنشاء العامل، يرجى المحاولة مجدداً")
            return worker
        db.refresh(worker)
        audit_crud.log_action(db, "create", "worker", worker.id, current_user_id, entity_label=worker.name)
    elif worker.is_deleted:
        # إعادة تفعيل العامل تلقائيًا لو تم اختياره مجددًا بعملية جديدة
        worker.is_deleted = False
        worker.deleted_by_id = None
        db.commit()
        db.refresh(worker)
    return worker


def get_workers(db: Session):
    return db.query(models.Worker)\
              .filter(models.Worker.is_deleted == False)\
              .order_by(models.Worker.name).all()


def update_worker(db: Session, worker_id: int, data: schemas.WorkerUpdate, current_user_id: int | None = None):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise ValueError("العامل غير موجود")
    # 🛡️ إصلاح: منع تعديل عامل مؤرشف مباشرة، يجب استعادته أولاً من الأرشيف
    if worker.is_deleted:
        raise ValueError("لا يمكن تعديل عامل مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        worker.name = data.name
    if data.phone is not None:
        worker.phone = data.phone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد عامل آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(worker)
    audit_crud.log_action(db, "update", "worker", worker.id, current_user_id, entity_label=worker.name)
    return worker


def soft_delete_worker(db: Session, worker_id: int, current_user_id: int):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise ValueError("العامل غير موجود")
    worker.is_deleted = True
    worker.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "worker", worker.id, current_user_id, entity_label=worker.name)
    return worker

def get_archived_workers(db: Session):
    workers = db.query(models.Worker)\
                .options(joinedload(models.Worker.deleted_by))\
                .filter(models.Worker.is_deleted == True)\
                .order_by(desc(models.Worker.id)).all()
    for w in workers:
        w.deleted_by_username = w.deleted_by.username if w.deleted_by else None
    return workers


def restore_worker(db: Session, worker_id: int, current_user_id: int):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise ValueError("العامل غير موجود")
    if not worker.is_deleted:
        raise ValueError("العامل غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود: منع الاستعادة لو يوجد عامل نشط حاليًا بنفس الاسم
    # (مستقل عن قيد unique بقاعدة البيانات، لإعطاء رسالة عربية واضحة بدل خطأ تقني)
    duplicate = db.query(models.Worker).filter(
        models.Worker.name == worker.name,
        models.Worker.is_deleted == False,
        models.Worker.id != worker.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة العامل، يوجد عامل نشط حاليًا بنفس الاسم '{worker.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    worker.is_deleted = False
    worker.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        # 🛡️ شبكة أمان لحالات التزامن النادرة يفلت منها الفحص المسبق أعلاه
        db.rollback()
        raise ValueError(f"لا يمكن استعادة العامل، يوجد عامل نشط حاليًا بنفس الاسم '{worker.name}'")
    db.refresh(worker)
    audit_crud.log_action(db, "restore", "worker", worker.id, current_user_id, entity_label=worker.name)
    return worker


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
    current_user_id: int,
    force: bool = False,
):
    stage = assembly.stage.value if hasattr(assembly.stage, 'value') else assembly.stage
    worker = get_or_create_worker(db, assembly.worker_name, current_user_id)

    all_records = db.query(models.AssemblyRecord)\
        .filter(models.AssemblyRecord.chassis_number == assembly.chassis_number)\
        .all()

    existing_stages = {r.stage for r in all_records}

    # ── تحديد النوع واللون المعروفين مسبقًا لهذا الهيكل (إن وجدا) ────────
    existing_type_id = next((r.bike_type_id for r in all_records if r.bike_type_id), None)
    existing_color_id = next((r.bike_color_id for r in all_records if r.bike_color_id), None)

    type_id = existing_type_id
    color_id = existing_color_id

    needs_type = stage in (STAGE_ASSEMBLY, STAGE_COMPLETE) and not existing_type_id
    needs_color = stage in (STAGE_COVER, STAGE_COMPLETE) and not existing_color_id

    if needs_type and not assembly.bike_type_name:
        raise HTTPException(status_code=422, detail="⛔ نوع الدراجة مطلوب لهذه المرحلة.")
    if needs_color and not assembly.bike_color_name:
        raise HTTPException(status_code=422, detail="⛔ لون الدراجة مطلوب لهذه المرحلة.")

    if needs_type:
        type_id = get_or_create_bike_type(db, assembly.bike_type_name, current_user_id).id
    if needs_color:
        color_id = get_or_create_bike_color(db, assembly.bike_color_name, current_user_id).id

    # ── باقي الفحوصات المنطقية (بدون أي تغيير) ───────────────────────────
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
            rec.recorded_by_id = current_user_id
            db.commit()
            db.refresh(rec)
            audit_crud.log_action(
                db, "create", "assembly", rec.id, current_user_id,
                entity_label=f"{assembly.chassis_number} — {_label(stage)}"
            )
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
        rec.recorded_by_id = current_user_id
        db.commit()
        db.refresh(rec)
        audit_crud.log_action(
            db, "create", "assembly", rec.id, current_user_id,
            entity_label=f"{assembly.chassis_number} — {_label(stage)}"
        )
        return rec

    # سجل جديد
    record = models.AssemblyRecord(
        chassis_number=assembly.chassis_number,
        worker_id=worker.id,
        stage=stage,
        bike_type_id=type_id,
        bike_color_id=color_id,
        recorded_by_id=current_user_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    audit_crud.log_action(
        db, "create", "assembly", record.id, current_user_id,
        entity_label=f"{assembly.chassis_number} — {_label(stage)}"
    )
    return record


def get_assembly_by_chassis(db: Session, chassis_number: str):
    return db.query(models.AssemblyRecord)\
              .filter(models.AssemblyRecord.chassis_number == chassis_number)\
              .order_by(models.AssemblyRecord.timestamp).all()


# ====================== BIKE TYPE ======================
def get_or_create_bike_type(db: Session, name: str, current_user_id: int | None = None):
    bike_type = db.query(models.BikeType).filter(models.BikeType.name == name).first()
    if not bike_type:
        bike_type = models.BikeType(name=name, created_by_id=current_user_id)
        db.add(bike_type)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            bike_type = db.query(models.BikeType).filter(models.BikeType.name == name).first()
            if not bike_type:
                raise ValueError("تعذر إنشاء نوع الدراجة، يرجى المحاولة مجدداً")
            return bike_type
        audit_crud.log_action(db, "create", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
        db.refresh(bike_type)
    elif bike_type.is_deleted:
        bike_type.is_deleted = False
        bike_type.deleted_by_id = None
        db.commit()
        db.refresh(bike_type)
    return bike_type

def get_bike_types(db: Session):
    return db.query(models.BikeType)\
              .filter(models.BikeType.is_deleted == False)\
              .order_by(models.BikeType.name).all()

def update_bike_type(db: Session, type_id: int, data: schemas.BikeTypeUpdate, current_user_id: int | None = None):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    # 🛡️ إصلاح: منع تعديل نوع دراجة مؤرشف مباشرة، يجب استعادته أولاً من الأرشيف
    if bike_type.is_deleted:
        raise ValueError("لا يمكن تعديل نوع دراجة مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        bike_type.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد نوع آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(bike_type)
    audit_crud.log_action(db, "update", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type

def soft_delete_bike_type(db: Session, type_id: int, current_user_id: int):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    bike_type.is_deleted = True
    bike_type.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type

def get_archived_bike_types(db: Session):
    types = db.query(models.BikeType)\
              .options(joinedload(models.BikeType.deleted_by))\
              .filter(models.BikeType.is_deleted == True)\
              .order_by(desc(models.BikeType.id)).all()
    for t in types:
        t.deleted_by_username = t.deleted_by.username if t.deleted_by else None
    return types


def restore_bike_type(db: Session, type_id: int, current_user_id: int):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    if not bike_type.is_deleted:
        raise ValueError("النوع غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود لإعطاء رسالة عربية واضحة (نفس نمط العملاء/العمال)
    duplicate = db.query(models.BikeType).filter(
        models.BikeType.name == bike_type.name,
        models.BikeType.is_deleted == False,
        models.BikeType.id != bike_type.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة النوع، يوجد نوع نشط حاليًا بنفس الاسم '{bike_type.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    bike_type.is_deleted = False
    bike_type.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"لا يمكن استعادة النوع، يوجد نوع نشط حاليًا بنفس الاسم '{bike_type.name}'")
    db.refresh(bike_type)
    audit_crud.log_action(db, "restore", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type


# ====================== BIKE COLOR ======================
def get_or_create_bike_color(db: Session, name: str, current_user_id: int | None = None):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.name == name).first()
    if not bike_color:
        bike_color = models.BikeColor(name=name, created_by_id=current_user_id)
        db.add(bike_color)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            bike_color = db.query(models.BikeColor).filter(models.BikeColor.name == name).first()
            if not bike_color:
                raise ValueError("تعذر إنشاء لون الدراجة، يرجى المحاولة مجدداً")
            return bike_color
        audit_crud.log_action(db, "create", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
        db.refresh(bike_color)
    elif bike_color.is_deleted:
        bike_color.is_deleted = False
        bike_color.deleted_by_id = None
        db.commit()
        db.refresh(bike_color)
    return bike_color


def get_bike_colors(db: Session):
    return db.query(models.BikeColor)\
              .filter(models.BikeColor.is_deleted == False)\
              .order_by(models.BikeColor.name).all()

def update_bike_color(db: Session, color_id: int, data: schemas.BikeColorUpdate, current_user_id: int | None = None):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    # 🛡️ إصلاح: منع تعديل لون دراجة مؤرشف مباشرة، يجب استعادته أولاً من الأرشيف
    if bike_color.is_deleted:
        raise ValueError("لا يمكن تعديل لون دراجة مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        bike_color.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد لون آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(bike_color)
    audit_crud.log_action(db, "update", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color

def soft_delete_bike_color(db: Session, color_id: int, current_user_id: int):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    bike_color.is_deleted = True
    bike_color.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color

def get_archived_bike_colors(db: Session):
    colors = db.query(models.BikeColor)\
               .options(joinedload(models.BikeColor.deleted_by))\
               .filter(models.BikeColor.is_deleted == True)\
               .order_by(desc(models.BikeColor.id)).all()
    for c in colors:
        c.deleted_by_username = c.deleted_by.username if c.deleted_by else None
    return colors


def restore_bike_color(db: Session, color_id: int, current_user_id: int):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    if not bike_color.is_deleted:
        raise ValueError("اللون غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود لإعطاء رسالة عربية واضحة (نفس نمط العملاء/العمال)
    duplicate = db.query(models.BikeColor).filter(
        models.BikeColor.name == bike_color.name,
        models.BikeColor.is_deleted == False,
        models.BikeColor.id != bike_color.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة اللون، يوجد لون نشط حاليًا بنفس الاسم '{bike_color.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    bike_color.is_deleted = False
    bike_color.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"لا يمكن استعادة اللون، يوجد لون نشط حاليًا بنفس الاسم '{bike_color.name}'")
    db.refresh(bike_color)
    audit_crud.log_action(db, "restore", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color