from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from datetime import datetime, time, timedelta
from . import models
from .time_utils import local_naive_to_utc


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None,
    user_id: int | None,
    entity_label: str | None = None,
    details: str | None = None,
):
    """
    يسجّل عملية واحدة في جدول اللوغ. تُستدعى من داخل دوال الـ crud الأخرى
    مباشرة بعد commit العملية الأصلية، بحيث لا تفشل العملية الأساسية أبداً
    بسبب فشل التسجيل (best-effort logging).
    """
    try:
        entry = models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            details=details,
            user_id=user_id,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()  # لا نكسر تدفق العملية الأساسية أبداً بسبب خطأ في اللوغ


def get_logs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
):
    q = db.query(models.AuditLog).options(joinedload(models.AuditLog.user))

    if action:
        q = q.filter(models.AuditLog.action == action)
    if entity_type:
        q = q.filter(models.AuditLog.entity_type == entity_type)
    if user_id:
        q = q.filter(models.AuditLog.user_id == user_id)
    # التواريخ القادمة من الواجهة (naive) تُفسَّر بتوقيت الجزائر ثم تُحوَّل إلى UTC
    # للمقارنة مع timestamp المخزَّن بـ UTC
    if date_from:
        q = q.filter(models.AuditLog.timestamp >= local_naive_to_utc(date_from))
    if date_to:
        if date_to.tzinfo is None and date_to.time() == time.min:
            # تاريخ بلا وقت (من حقل type="date"): يشمل اليوم كاملًا، أي حتى بداية اليوم التالي
            q = q.filter(models.AuditLog.timestamp < local_naive_to_utc(date_to + timedelta(days=1)))
        else:
            q = q.filter(models.AuditLog.timestamp <= local_naive_to_utc(date_to))
    if search:
        like = f"%{search}%"
        q = q.filter(models.AuditLog.entity_label.ilike(like))

    total = q.count()
    logs = q.order_by(desc(models.AuditLog.timestamp)).offset(skip).limit(limit).all()

    for log in logs:
        log.username = log.user.username if log.user else None
        log.user_full_name = log.user.full_name if log.user else None

    return logs, total


def get_log_by_id(db: Session, log_id: int):
    log = db.query(models.AuditLog)\
            .options(joinedload(models.AuditLog.user))\
            .filter(models.AuditLog.id == log_id).first()
    if log:
        log.username = log.user.username if log.user else None
        log.user_full_name = log.user.full_name if log.user else None
    return log
