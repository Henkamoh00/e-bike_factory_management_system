from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas, audit_crud
from ..security import get_current_user, require_roles

router = APIRouter(prefix="/api/roles", tags=["roles"])

admin_only = require_roles(models.RoleNames.ADMIN)


def _sanitize_tabs(tabs: list[str] | None) -> list[str]:
    """يستبعد أي معرّف تبويب غير معروف (حماية من إدخال عشوائي)"""
    return [t for t in (tabs or []) if t in schemas.ALL_TAB_IDS]


def _to_response(db: Session, role: models.Role) -> schemas.RoleResponse:
    count = db.query(func.count(models.User.id)).filter(
        models.User.role_id == role.id,
        models.User.is_deleted.is_(False)
    ).scalar() or 0
    return schemas.RoleResponse(
        id=role.id, name=role.name, label=role.label,
        description=role.description, is_system=role.is_system,
        allowed_tabs=role.allowed_tabs or [],
        users_count=count
    )


@router.get("/", response_model=list[schemas.RoleResponse])
def get_roles(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    roles = db.query(models.Role).order_by(models.Role.id).all()
    return [_to_response(db, r) for r in roles]


@router.post("/", response_model=schemas.RoleResponse)
def create_role(
    data: schemas.RoleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only),
):
    name = data.name.strip().lower().replace(" ", "_")
    if not name:
        raise HTTPException(status_code=400, detail="اسم الدور مطلوب")
    existing = db.query(models.Role).filter(models.Role.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="اسم الدور موجود مسبقاً")

    role = models.Role(
        name=name,
        label=data.label,
        description=data.description,
        is_system=False,
        allowed_tabs=_sanitize_tabs(data.allowed_tabs),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    audit_crud.log_action(db, "create", "role", role.id, current_user.id, entity_label=role.label)
    return _to_response(db, role)


@router.put("/{role_id}/", response_model=schemas.RoleResponse)
def update_role(
    role_id: int,
    data: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only),
):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="الدور غير موجود")

    if data.label is not None:
        role.label = data.label
    if data.description is not None:
        role.description = data.description

    if data.allowed_tabs is not None:
        # 🛡️ حماية حاسمة: لا يمكن تقييد صلاحيات دور admin أبداً، مهما أرسل الطلب
        # يمنع هذا قفل النظام بالكامل بالخطأ (لا يبقى أي مستخدم بصلاحية كاملة)
        if role.name == models.RoleNames.ADMIN:
            role.allowed_tabs = list(schemas.ALL_TAB_IDS)
        else:
            role.allowed_tabs = _sanitize_tabs(data.allowed_tabs)

    db.commit()
    db.refresh(role)
    audit_crud.log_action(db, "update", "role", role.id, current_user.id, entity_label=role.label)
    return _to_response(db, role)


@router.delete("/{role_id}/")
def delete_role(role_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(admin_only)):
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="الدور غير موجود")
    if role.is_system:
        raise HTTPException(status_code=400, detail="لا يمكن حذف أحد أدوار النظام الأساسية (admin/supervisor/operator)")

    in_use = db.query(func.count(models.User.id)).filter(
        models.User.role_id == role.id,
        models.User.is_deleted.is_(False)
    ).scalar() or 0
    if in_use > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف هذا الدور، يوجد {in_use} مستخدم مرتبط به حالياً")

    db.delete(role)
    db.commit()
    audit_crud.log_action(db, "delete", "role", role_id, current_user.id, entity_label=role.label)
    return {"message": "تم حذف الدور بنجاح", "status": "success"}
