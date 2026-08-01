from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from .. import schemas, models, audit_crud
from ..security import require_tab

router = APIRouter(prefix="/api/logs", tags=["logs"])

# 🛡️ الوصول أصبح تابعًا لصلاحية التبويب "logs" الممنوحة ديناميكيًا من إدارة الأدوار
# (admin يملكها دائمًا تلقائيًا، وأي دور آخر فقط إن مُنح تبويب "سجل النشاط" صراحة)
can_view_logs = require_tab("logs")

ACTION_CHOICES = [
    "create", "update", "delete", "cancel", "restore", "repair", "login",
    "bulk_delete", "bulk_cancel", "bulk_restore", "bulk_repair",
    "bulk_activate", "bulk_deactivate"
]
ENTITY_CHOICES = ["worker", "customer", "bike_type", "bike_color", "assembly", "sale", "fault", "fault_repair", "user", "role"]


@router.get("/", response_model=schemas.AuditLogListResponse)
def get_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = Query(default=None, description="بحث في وصف السجل (مثال: رقم هيكل أو اسم)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_logs),
):
    logs, total = audit_crud.get_logs(
        db, skip=skip, limit=limit, action=action, entity_type=entity_type,
        user_id=user_id, date_from=date_from, date_to=date_to, search=search
    )
    return {"items": logs, "total": total}


@router.get("/meta/")
def get_logs_meta(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_logs)):
    users = db.query(models.User).filter(models.User.is_deleted == False).order_by(models.User.username).all()
    return {
        "actions": ACTION_CHOICES,
        "entity_types": ENTITY_CHOICES,
        "users": [{"id": u.id, "label": u.full_name or u.username} for u in users],
    }


@router.get("/{log_id}/", response_model=schemas.AuditLogResponse)
def get_log_detail(log_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_logs)):
    log = audit_crud.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    return log