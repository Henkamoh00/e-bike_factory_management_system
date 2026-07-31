from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from . import models, schemas
from .security import hash_password, verify_password


def _get_role_by_name(db: Session, name: str) -> models.Role:
    role = db.query(models.Role).filter(models.Role.name == name).first()
    if not role:
        raise ValueError(f"الدور '{name}' غير موجود")
    return role


def _attach_role(user: models.User) -> models.User:
    """يُلحق role و role_label و allowed_tabs، مطلوب لكل استجابة UserResponse"""
    if user.role_obj:
        user.role = user.role_obj.name
        user.role_label = user.role_obj.label
        # 🛡️ admin دائمًا بكل الصلاحيات، بغض النظر عن المخزّن فعليًا في قاعدة البيانات
        if user.role_obj.name == models.RoleNames.ADMIN:
            user.allowed_tabs = list(schemas.ALL_TAB_IDS)
        else:
            user.allowed_tabs = user.role_obj.allowed_tabs or []
    return user


def create_user(db: Session, data: schemas.UserCreate):
    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing:
        raise ValueError("اسم المستخدم موجود مسبقاً")

    role = _get_role_by_name(db, data.role)

    user = models.User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _attach_role(user)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).options(joinedload(models.User.role_obj)).filter(
        models.User.username == username,
        models.User.is_deleted == False
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return _attach_role(user)


def get_users(db: Session):
    users = db.query(models.User)\
              .options(joinedload(models.User.role_obj))\
              .filter(models.User.is_deleted == False)\
              .order_by(models.User.id.desc()).all()
    return [_attach_role(u) for u in users]


def update_user(db: Session, user_id: int, data: schemas.UserUpdate):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        role = _get_role_by_name(db, data.role)
        user.role_id = role.id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return _attach_role(user)


def soft_delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    user.is_deleted = True
    user.is_active = False
    db.commit()
    return user


def bulk_deactivate_users(db: Session, ids: list[int], current_user_id: int):
    ids = [i for i in ids if i != current_user_id]
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    for u in users:
        u.is_active = False
    db.commit()
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم تعطيل {len(users)} مستخدم"}


def bulk_activate_users(db: Session, ids: list[int]):
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    for u in users:
        u.is_active = True
    db.commit()
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم تفعيل {len(users)} مستخدم"}


def bulk_soft_delete_users(db: Session, ids: list[int], current_user_id: int):
    ids = [i for i in ids if i != current_user_id]
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    for u in users:
        u.is_deleted = True
        u.is_active = False
    db.commit()
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم حذف {len(users)} مستخدم"}