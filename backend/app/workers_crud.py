from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from . import models, schemas, audit_crud


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


def get_workers(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    """
    🆕 نسخة مُصفَّحة (Paginated) من قائمة العمال البسيطة.
    تُرجع Tuple: (العناصر، الإجمالي) بدل قائمة كاملة.
    """
    query = db.query(models.Worker).filter(models.Worker.is_deleted.is_(False))
    if search:
        query = query.filter(models.Worker.name.ilike(f"%{search}%"))
    total = query.count()
    items = query.order_by(models.Worker.name).offset(skip).limit(limit).all()
    return items, total


def search_workers_simple(db: Session, q: str | None = None, limit: int = 20):
    """
    🆕 بحث خفيف للقوائم المنسدلة (SearchableSelect):
    يرجع فقط id/name، بدون سجلات، ومحدود بـ limit صارم.
    لا يُستخدم للعرض الجدولي، بل لتغذية الـ dropdowns ديناميكيًا.
    """
    query = db.query(models.Worker).filter(models.Worker.is_deleted.is_(False))
    if q:
        query = query.filter(models.Worker.name.ilike(f"%{q}%"))
    return query.order_by(models.Worker.name).limit(limit).all()


def update_worker(db: Session, worker_id: int, data: schemas.WorkerUpdate, current_user_id: int | None = None):
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        raise ValueError("العامل غير موجود")
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


def get_archived_workers(db: Session, skip: int = 0, limit: int = 20):
    query = db.query(models.Worker)\
              .options(joinedload(models.Worker.deleted_by))\
              .filter(models.Worker.is_deleted.is_(True))\
              .order_by(desc(models.Worker.id))
    total = query.count()
    workers = query.offset(skip).limit(limit).all()
    for w in workers:
        w.deleted_by_username = w.deleted_by.username if w.deleted_by else None
    return workers, total


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
        models.Worker.is_deleted.is_(False),
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
