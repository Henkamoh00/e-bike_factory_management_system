from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from . import models, schemas, audit_crud
from .security import hash_password, verify_password
from datetime import datetime, timedelta, timezone
from .models import RefreshToken


# توجد مشكلة في طريقة تعريف الوقت ومقرانة الحقول المتعلقة بالوقت المجلوبة من قاعدة البيانات
# الطرق المختلفة مثل التاريخ مرتبط بالمنطقة الزمنية وبدونه
# datetime.now_utc()
# datetime.utcnow()
# datetime.now(timezone.utc).replace(tzinfo=None)
# datetime.now(timezone.utc)
# 📌 راجع backend/NOTES.md — قسم "تضارب محتمل في طريقة التعامل مع الوقت (timezone)"


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


def get_users(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    """🆕 مُصفَّحة الآن: تُرجع Tuple (items, total)"""
    query = db.query(models.User)\
              .options(joinedload(models.User.role_obj))\
              .filter(models.User.is_deleted == False)

    if search:
        query = query.filter(models.User.username.ilike(f"%{search}%"))

    total = query.count()
    users = query.order_by(models.User.id.desc()).offset(skip).limit(limit).all()
    return [_attach_role(u) for u in users], total


def update_user(db: Session, user_id: int, data: schemas.UserUpdate, current_user_id: int | None = None):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")

    if user.is_deleted:
        raise ValueError("لا يمكن تعديل مستخدم مؤرشف، يجب استعادته أولاً")

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

    password_changed = False
    if data.password:
        changes.append("تم تغيير كلمة المرور")
        user.hashed_password = hash_password(data.password)
        password_changed = True

    db.commit()
    db.refresh(user)

    # 🛡️ عند تغيير كلمة المرور: إبطال كل refresh tokens الحالية للمستخدم فورًا.
    # بدون هذا، أي جهاز يملك refresh token قديم (مثلاً جهاز مخترق) يبقى قادرًا
    # على تجديد access token رغم تغيير كلمة المرور، مما يُفشل الغرض الأمني من الخطوة.
    if password_changed:
        revoke_all_user_tokens(db, user.id)

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
    # 🛡️ إبطال كل جلسات المستخدم فورًا عند الحذف الناعم، حتى لا يبقى بإمكانه
    # تجديد access token عبر refresh token قديم رغم أرشفة حسابه
    revoke_all_user_tokens(db, user.id)
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
    # 🛡️ إبطال جلسات كل مستخدم عُطِّل، لنفس السبب أعلاه
    for u in users:
        revoke_all_user_tokens(db, u.id)
    audit_crud.log_action(
        db, "bulk_deactivate", "user", None, current_user_id,
        entity_label=f"{len(users)} مستخدم", details="، ".join(names) if names else None
    )
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم تعطيل {len(users)} مستخدم"}


def bulk_activate_users(db: Session, ids: list[int], current_user_id: int | None = None):
    # 🛡️ إصلاح: استبعاد المستخدمين المؤرشفين (is_deleted=True) من التفعيل الجماعي
    # حتى لا تنتج حالة بيانات متضاربة (is_deleted=True مع is_active=True)
    # ولا يتم تفعيلهم إلا عبر مسار /restore/ المحصور بالأدمن فقط
    users = db.query(models.User).filter(
        models.User.id.in_(ids),
        models.User.is_deleted == False
    ).all()
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
    # 🛡️ إبطال جلسات كل مستخدم حُذف حذفًا ناعمًا جماعيًا
    for u in users:
        revoke_all_user_tokens(db, u.id)
    audit_crud.log_action(
        db, "bulk_delete", "user", None, current_user_id,
        entity_label=f"{len(users)} مستخدم", details="، ".join(names) if names else None
    )
    return {"success_count": len(users), "failed_ids": failed_ids, "message": f"تم حذف {len(users)} مستخدم"}


# ====================== أرشيف المستخدمين ======================
def get_archived_users(db: Session, skip: int = 0, limit: int = 20):
    query = db.query(models.User)\
              .options(joinedload(models.User.role_obj), joinedload(models.User.deleted_by))\
              .filter(models.User.is_deleted == True)\
              .order_by(desc(models.User.id))
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    for u in users:
        u.role_label = u.role_obj.label if u.role_obj else None
        u.deleted_by_username = u.deleted_by.username if u.deleted_by else None
    return users, total


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


def create_refresh_token(db: Session, user_id: int, days_valid: int, user_agent: str | None = None, ip_address: str | None = None) -> str:
    """ينشئ refresh token جديد، يخزّن الهاش فقط، ويرجع القيمة الخام (لتُوضع في الكوكي مرة واحدة فقط)"""
    raw_token = RefreshToken.generate_raw_token()
    db_token = RefreshToken(
        token_hash=RefreshToken.hash_token(raw_token),
        user_id=user_id,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days_valid),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(db_token)
    db.commit()
    return raw_token


def verify_and_rotate_refresh_token(db: Session, raw_token: str) -> models.User | None:
    """
    🛡️ يتحقق من صلاحية الـ refresh token ثم يُبطله فورًا (rotation) —
    كل استخدام لتوكن التحديث يُنتج توكنًا جديدًا ويُلغي القديم.
    هذا يمنع إعادة استخدام توكن مسروق قديم (replay attack)، ويكشف السرقة:
    لو استُخدم توكن مُبطَل سابقًا، فهذا مؤشر قوي على أن نسخة منه سُرِّبت.
    """
    token_hash = RefreshToken.hash_token(raw_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not db_token:
        return None

    if db_token.revoked:
        # 🛡️ إبطال احترازي شامل: لو توكن مُبطَل استُخدم مجددًا، على الأرجح سُرِّب.
        # نُبطل كل توكنات هذا المستخدم فورًا كإجراء احترازي (يجبره على تسجيل دخول جديد بكل الأجهزة)
        db.query(RefreshToken).filter(
            RefreshToken.user_id == db_token.user_id,
            RefreshToken.revoked == False
        ).update({"revoked": True})
        db.commit()
        return None

    if db_token.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None

    user = db.query(models.User).filter(
        models.User.id == db_token.user_id,
        models.User.is_deleted == False
    ).first()
    if not user or not user.is_active:
        return None

    # إبطال التوكن الحالي فورًا بعد التحقق (rotation)
    db_token.revoked = True
    db.commit()

    return _attach_role(user)


def revoke_refresh_token(db: Session, raw_token: str):
    """يُستخدم عند تسجيل الخروج"""
    token_hash = RefreshToken.hash_token(raw_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if db_token:
        db_token.revoked = True
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: int):
    """يُستخدم عند تغيير كلمة المرور، تعطيل/حذف المستخدم، أو الاشتباه بالاختراق"""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()
