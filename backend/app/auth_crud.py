from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from . import models, schemas, audit_crud
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
        if user.role_obj.name == models.RoleNames.ADMIN:
            user.allowed_tabs = list(schemas.ALL_TAB_IDS)
        else:
            user.allowed_tabs = user.role_obj.allowed_tabs or []
    return user


def create_user(db: Session, data: schemas.UserCreate, current_user_id: int | None = None):
    # 🛡️ فحص مسبق بالكود: يستثني المستخدمين المؤرشفين (is_deleted=True)
    # حتى لا يبقى اسم المستخدم "محجوزًا للأبد" بعد الحذف الناعم
    existing = db.query(models.User).filter(
        models.User.username == data.username,
        models.User.is_deleted == False
    ).first()
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
    try:
        db.commit()
    except IntegrityError:
        # 🛡️ شبكة أمان لحالات التزامن النادرة يفلت منها الفحص المسبق أعلاه
        db.rollback()
        raise ValueError("اسم المستخدم موجود مسبقاً")
    db.refresh(user)
    audit_crud.log_action(db, "create", "user", user.id, current_user_id, entity_label=user.username)
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


def update_user(db: Session, user_id: int, data: schemas.UserUpdate, current_user_id: int | None = None):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")

    changes = []
    if data.full_name is not None and data.full_name != user.full_name:
        changes.append(f"الاسم الكامل → {data.full_name}")
        user.full_name = data.full_name
    if data.role is not None:
        role = _get_role_by_name(db, data.role)
        if role.id != user.role_id:
            changes.append(f"الدور → {role.label}")
        user.role_id = role.id
    if data.is_active is not None and data.is_active != user.is_active:
        changes.append("تم التفعيل" if data.is_active else "تم التعطيل")
        user.is_active = data.is_active
    if data.password:
        changes.append("تم تغيير كلمة المرور")
        user.hashed_password = hash_password(data.password)

    db.commit()
    db.refresh(user)
    audit_crud.log_action(
        db, "update", "user", user.id, current_user_id,
        entity_label=user.username, details="، ".join(changes) if changes else None
    )
    return _attach_role(user)


def soft_delete_user(db: Session, user_id: int, current_user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    user.is_deleted = True
    user.is_active = False
    user.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "user", user.id, current_user_id, entity_label=user.username)
    return user


def bulk_deactivate_users(db: Session, ids: list[int], current_user_id: int):
    ids = [i for i in ids if i != current_user_id]
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [u.username for u in users]
    for u in users:
        u.is_active = False
    db.commit()
    audit_crud.log_action(
        db, "bulk_deactivate", "user", None, current_user_id,
        entity_label=f"{len(users)} مستخدم", details="، ".join(names) if names else None
    )
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم تعطيل {len(users)} مستخدم"}


def bulk_activate_users(db: Session, ids: list[int], current_user_id: int | None = None):
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [u.username for u in users]
    for u in users:
        u.is_active = True
    db.commit()
    audit_crud.log_action(
        db, "bulk_activate", "user", None, current_user_id,
        entity_label=f"{len(users)} مستخدم", details="، ".join(names) if names else None
    )
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم تفعيل {len(users)} مستخدم"}


def bulk_soft_delete_users(db: Session, ids: list[int], current_user_id: int):
    ids = [i for i in ids if i != current_user_id]
    users = db.query(models.User).filter(models.User.id.in_(ids)).all()
    found_ids = {u.id for u in users}
    failed_ids = [i for i in ids if i not in found_ids]
    names = [u.username for u in users]
    for u in users:
        u.is_deleted = True
        u.is_active = False
        u.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(
        db, "bulk_delete", "user", None, current_user_id,
        entity_label=f"{len(users)} مستخدم", details="، ".join(names) if names else None
    )
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم حذف {len(users)} مستخدم"}


# ====================== أرشيف المستخدمين ======================
def get_archived_users(db: Session):
    users = db.query(models.User)\
              .options(joinedload(models.User.role_obj), joinedload(models.User.deleted_by))\
              .filter(models.User.is_deleted == True)\
              .order_by(desc(models.User.id)).all()
    for u in users:
        u.role_label = u.role_obj.label if u.role_obj else None
        u.deleted_by_username = u.deleted_by.username if u.deleted_by else None
    return users


def restore_user(db: Session, user_id: int, current_user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    if not user.is_deleted:
        raise ValueError("المستخدم غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود: منع الاستعادة لو يوجد مستخدم نشط حاليًا بنفس اسم المستخدم
    duplicate = db.query(models.User).filter(
        models.User.username == user.username,
        models.User.is_deleted == False,
        models.User.id != user.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة المستخدم، يوجد مستخدم نشط حاليًا بنفس اسم المستخدم '{user.username}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    user.is_deleted = False
    user.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        # 🛡️ شبكة أمان لحالات التزامن النادرة يفلت منها الفحص المسبق أعلاه
        db.rollback()
        raise ValueError(f"لا يمكن استعادة المستخدم، يوجد مستخدم نشط حاليًا بنفس اسم المستخدم '{user.username}'")
    audit_crud.log_action(db, "restore", "user", user.id, current_user_id, entity_label=user.username)
    return user