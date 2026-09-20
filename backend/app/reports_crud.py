from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from . import models, audit_crud


# ====================== WORKERS (تقرير للوحة الإدارة) ======================
def get_workers_with_records(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.Worker).filter(models.Worker.is_deleted.is_(False))
    if search:
        query = query.filter(models.Worker.name.ilike(f"%{search}%"))

    total = query.count()
    workers = query.order_by(desc(models.Worker.id)).offset(skip).limit(limit).all()

    if not workers:
        return [], total

    worker_ids = [w.id for w in workers]
    all_records = db.query(models.AssemblyRecord)\
        .filter(models.AssemblyRecord.worker_id.in_(worker_ids))\
        .order_by(models.AssemblyRecord.timestamp)\
        .all()

    records_by_worker = {}
    for r in all_records:
        records_by_worker.setdefault(r.worker_id, []).append(r)

    result = []
    for w in workers:
        records = records_by_worker.get(w.id, [])
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


def bulk_soft_delete_workers(db: Session, ids: list[int], current_user_id: int):
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


# ====================== BIKE TYPES / COLORS (تقرير للوحة الإدارة) ======================
def get_bike_types_with_usage(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.BikeType).filter(models.BikeType.is_deleted.is_(False))
    if search:
        query = query.filter(models.BikeType.name.ilike(f"%{search}%"))

    total = query.count()
    types = query.order_by(desc(models.BikeType.id)).offset(skip).limit(limit).all()

    if not types:
        return [], total

    type_ids = [t.id for t in types]
    usage_rows = (
        db.query(models.AssemblyRecord.bike_type_id, func.count(models.AssemblyRecord.id))
        .filter(models.AssemblyRecord.bike_type_id.in_(type_ids))
        .group_by(models.AssemblyRecord.bike_type_id)
        .all()
    )
    usage_by_type = {row[0]: row[1] for row in usage_rows}

    result = [
        {
            "id": t.id,
            "name": t.name,
            "usage_count": usage_by_type.get(t.id, 0),
            # 🆕 يُعرض في واجهة إعدادات أنواع الدراجات
            "default_price": t.default_price,
        }
        for t in types
    ]
    return result, total


def get_bike_colors_with_usage(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.BikeColor).filter(models.BikeColor.is_deleted.is_(False))
    if search:
        query = query.filter(models.BikeColor.name.ilike(f"%{search}%"))

    total = query.count()
    colors = query.order_by(desc(models.BikeColor.id)).offset(skip).limit(limit).all()

    if not colors:
        return [], total

    color_ids = [c.id for c in colors]
    usage_rows = (
        db.query(models.AssemblyRecord.bike_color_id, func.count(models.AssemblyRecord.id))
        .filter(models.AssemblyRecord.bike_color_id.in_(color_ids))
        .group_by(models.AssemblyRecord.bike_color_id)
        .all()
    )
    usage_by_color = {row[0]: row[1] for row in usage_rows}

    result = [
        {"id": c.id, "name": c.name, "usage_count": usage_by_color.get(c.id, 0)}
        for c in colors
    ]
    return result, total


def bulk_soft_delete_bike_types(db: Session, ids: list[int], current_user_id: int):
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


def bulk_soft_delete_bike_colors(db: Session, ids: list[int], current_user_id: int):
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
