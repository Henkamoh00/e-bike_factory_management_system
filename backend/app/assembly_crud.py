from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from . import models, schemas, audit_crud, workers_crud, bike_options_crud


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


def create_assembly_record(
    db: Session,
    assembly: schemas.AssemblyCreate,
    current_user_id: int,
    force: bool = False,
):
    stage = assembly.stage.value if hasattr(assembly.stage, 'value') else assembly.stage
    worker = workers_crud.get_or_create_worker(db, assembly.worker_name, current_user_id)

    # 🛡️🛡️ خط الدفاع الأول ضد Race Condition: SELECT ... FOR UPDATE
    # يقفل كل السجلات الحالية المرتبطة بهذا الهيكل تحديدًا (على مستوى الصفوف)
    # داخل معاملة قاعدة البيانات الحالية. أي طلب متزامن آخر لنفس chassis_number
    # (بما فيه طلب إنشاء أول سجل من الصفر) سينتظر في طابور حتى ينتهي commit
    # لهذه المعاملة، بدل أن يقرأ الاثنان "لا يوجد سجل بهذه المرحلة" في نفس
    # اللحظة ويُدخلا سجلين متضاربين معًا.
    # ⚠️ ملاحظة: with_for_update() فعّال مع PostgreSQL/MySQL؛ يُتجاهل بصمت
    # على SQLite (لا قفل صفّي فيها أصلاً) — لذا القيد الفريد في models.py
    # (UNIQUE constraint) هو الضمانة الحقيقية والنهائية بغض النظر عن المحرك.
    all_records = db.query(models.AssemblyRecord)\
        .filter(models.AssemblyRecord.chassis_number == assembly.chassis_number)\
        .with_for_update()\
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
        type_id = bike_options_crud.get_or_create_bike_type(db, assembly.bike_type_name, current_user_id).id
    if needs_color:
        color_id = bike_options_crud.get_or_create_bike_color(db, assembly.bike_color_name, current_user_id).id

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
    try:
        db.commit()
    except IntegrityError:
        # 🛡️🛡️ خط الدفاع الثاني والنهائي: شبكة أمان تلتقط UNIQUE constraint
        # violation في الحالة النادرة جدًا التي يفلت منها القفل أعلاه
        # (مثلاً: قاعدة بيانات لا تدعم SELECT FOR UPDATE بنفس الصرامة،
        # أو مستوى عزل معاملات مختلف). بدل رمي خطأ 500 غامض للمستخدم،
        # نُرجع رسالة عربية واضحة تفيد بأن التسجيل تم فعليًا من جهة أخرى
        # في نفس اللحظة تقريبًا.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"🚫 تم تسجيل مرحلة '{_label(stage)}' لهذا الهيكل ({assembly.chassis_number}) للتو من جهاز أو حساب آخر. يرجى تحديث الصفحة والمحاولة مجدداً."
        )
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