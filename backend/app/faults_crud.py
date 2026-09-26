from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from . import models, schemas, workers_crud, assembly_crud, audit_crud


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


def _find_responsible_record(db: Session, chassis_number: str, related_stage: str):

    if not related_stage:
        return None
    record = (
        db.query(models.AssemblyRecord)
        .filter(
            models.AssemblyRecord.chassis_number == chassis_number,
            models.AssemblyRecord.stage == related_stage
        )
        .first()
    )
    if not record:
        record = (
            db.query(models.AssemblyRecord)
            .filter(
                models.AssemblyRecord.chassis_number == chassis_number,
                models.AssemblyRecord.stage == assembly_crud.STAGE_COMPLETE
            )
            .first()
        )
    return record


def _attach_fault_extras(db: Session, faults):
    for fault in faults:
        for repair in fault.repairs:
            repair.worker_name = repair.worker.name if repair.worker else "غير معروف"
            repair.recorded_by_username = repair.recorded_by.username if repair.recorded_by else None

        fault.reported_by_username = fault.reported_by.username if fault.reported_by else None
        fault.cancelled_by_username = fault.cancelled_by.username if fault.cancelled_by else None

        fault.responsible_worker_name = None
        record = _find_responsible_record(db, fault.chassis_number, fault.related_stage)
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
    query = db.query(models.Fault)

    if chassis_number:
        query = query.filter(models.Fault.chassis_number.ilike(f"%{chassis_number}%"))
    if status:
        query = query.filter(models.Fault.status == status)

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

    worker = workers_crud.get_or_create_worker(db, repair.worker_name, current_user_id)

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

    # 🛡️ إصلاح: كانت هذه الدالة تبحث فقط عن سجل بنفس المرحلة الدقيقة،
    # فلا تجد شيئًا إن كان العامل نفّذ المرحلتين معًا عبر 'تجميع_كامل' —
    # الآن تستخدم نفس منطق الرجوع الاحتياطي المستخدم في قائمة الأعطال
    record = _find_responsible_record(db, db_fault.chassis_number, db_fault.related_stage)
    if record and record.worker:
        return {"worker_id": record.worker.id, "worker_name": record.worker.name}
    return None


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


def bulk_mark_faults_fixed(db: Session, ids: list[int], worker_name: str, current_user_id: int):
    worker = workers_crud.get_or_create_worker(db, worker_name, current_user_id)
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
