from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from . import models, schemas, audit_crud


# ====================== BIKE TYPE ======================
def get_or_create_bike_type(db: Session, name: str, current_user_id: int | None = None):
    bike_type = db.query(models.BikeType).filter(models.BikeType.name == name).first()
    if not bike_type:
        bike_type = models.BikeType(name=name, created_by_id=current_user_id)
        db.add(bike_type)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            bike_type = db.query(models.BikeType).filter(models.BikeType.name == name).first()
            if not bike_type:
                raise ValueError("تعذر إنشاء نوع الدراجة، يرجى المحاولة مجدداً")
            return bike_type
        audit_crud.log_action(db, "create", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
        db.refresh(bike_type)
    elif bike_type.is_deleted:
        bike_type.is_deleted = False
        bike_type.deleted_by_id = None
        db.commit()
        db.refresh(bike_type)
    return bike_type

def search_bike_types_simple(db: Session, q: str | None = None, limit: int = 20):
    query = db.query(models.BikeType).filter(models.BikeType.is_deleted == False)
    if q:
        query = query.filter(models.BikeType.name.ilike(f"%{q}%"))
    return query.order_by(models.BikeType.name).limit(limit).all()

def update_bike_type(db: Session, type_id: int, data: schemas.BikeTypeUpdate, current_user_id: int | None = None):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    # 🛡️ إصلاح: منع تعديل نوع دراجة مؤرشف مباشرة، يجب استعادته أولاً من الأرشيف
    if bike_type.is_deleted:
        raise ValueError("لا يمكن تعديل نوع دراجة مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        bike_type.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد نوع آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(bike_type)
    audit_crud.log_action(db, "update", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type

def soft_delete_bike_type(db: Session, type_id: int, current_user_id: int):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    bike_type.is_deleted = True
    bike_type.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type

def get_archived_bike_types(db: Session, skip: int = 0, limit: int = 20):
    query = db.query(models.BikeType)\
              .options(joinedload(models.BikeType.deleted_by))\
              .filter(models.BikeType.is_deleted == True)\
              .order_by(desc(models.BikeType.id))
    total = query.count()
    types = query.offset(skip).limit(limit).all()
    for t in types:
        t.deleted_by_username = t.deleted_by.username if t.deleted_by else None
    return types, total


def restore_bike_type(db: Session, type_id: int, current_user_id: int):
    bike_type = db.query(models.BikeType).filter(models.BikeType.id == type_id).first()
    if not bike_type:
        raise ValueError("نوع الدراجة غير موجود")
    if not bike_type.is_deleted:
        raise ValueError("النوع غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود لإعطاء رسالة عربية واضحة (نفس نمط العملاء/العمال)
    duplicate = db.query(models.BikeType).filter(
        models.BikeType.name == bike_type.name,
        models.BikeType.is_deleted == False,
        models.BikeType.id != bike_type.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة النوع، يوجد نوع نشط حاليًا بنفس الاسم '{bike_type.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    bike_type.is_deleted = False
    bike_type.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"لا يمكن استعادة النوع، يوجد نوع نشط حاليًا بنفس الاسم '{bike_type.name}'")
    db.refresh(bike_type)
    audit_crud.log_action(db, "restore", "bike_type", bike_type.id, current_user_id, entity_label=bike_type.name)
    return bike_type


# ====================== BIKE COLOR ======================
def get_or_create_bike_color(db: Session, name: str, current_user_id: int | None = None):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.name == name).first()
    if not bike_color:
        bike_color = models.BikeColor(name=name, created_by_id=current_user_id)
        db.add(bike_color)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            bike_color = db.query(models.BikeColor).filter(models.BikeColor.name == name).first()
            if not bike_color:
                raise ValueError("تعذر إنشاء لون الدراجة، يرجى المحاولة مجدداً")
            return bike_color
        audit_crud.log_action(db, "create", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
        db.refresh(bike_color)
    elif bike_color.is_deleted:
        bike_color.is_deleted = False
        bike_color.deleted_by_id = None
        db.commit()
        db.refresh(bike_color)
    return bike_color


def search_bike_colors_simple(db: Session, q: str | None = None, limit: int = 20):
    query = db.query(models.BikeColor).filter(models.BikeColor.is_deleted == False)
    if q:
        query = query.filter(models.BikeColor.name.ilike(f"%{q}%"))
    return query.order_by(models.BikeColor.name).limit(limit).all()

def update_bike_color(db: Session, color_id: int, data: schemas.BikeColorUpdate, current_user_id: int | None = None):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    # 🛡️ إصلاح: منع تعديل لون دراجة مؤرشف مباشرة، يجب استعادته أولاً من الأرشيف
    if bike_color.is_deleted:
        raise ValueError("لا يمكن تعديل لون دراجة مؤرشف، يجب استعادته أولاً")
    if data.name is not None:
        bike_color.name = data.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"يوجد لون آخر بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(bike_color)
    audit_crud.log_action(db, "update", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color

def soft_delete_bike_color(db: Session, color_id: int, current_user_id: int):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    bike_color.is_deleted = True
    bike_color.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color

def get_archived_bike_colors(db: Session, skip: int = 0, limit: int = 20):
    query = db.query(models.BikeColor)\
              .options(joinedload(models.BikeColor.deleted_by))\
              .filter(models.BikeColor.is_deleted == True)\
              .order_by(desc(models.BikeColor.id))
    total = query.count()
    colors = query.offset(skip).limit(limit).all()
    for c in colors:
        c.deleted_by_username = c.deleted_by.username if c.deleted_by else None
    return colors, total


def restore_bike_color(db: Session, color_id: int, current_user_id: int):
    bike_color = db.query(models.BikeColor).filter(models.BikeColor.id == color_id).first()
    if not bike_color:
        raise ValueError("لون الدراجة غير موجود")
    if not bike_color.is_deleted:
        raise ValueError("اللون غير مؤرشف أصلاً")

    # 🛡️ فحص مسبق بالكود لإعطاء رسالة عربية واضحة (نفس نمط العملاء/العمال)
    duplicate = db.query(models.BikeColor).filter(
        models.BikeColor.name == bike_color.name,
        models.BikeColor.is_deleted == False,
        models.BikeColor.id != bike_color.id
    ).first()
    if duplicate:
        raise ValueError(
            f"لا يمكن استعادة اللون، يوجد لون نشط حاليًا بنفس الاسم '{bike_color.name}'. "
            f"يرجى تعديل اسم أحدهما أو حذف المكرر أولاً."
        )

    bike_color.is_deleted = False
    bike_color.deleted_by_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"لا يمكن استعادة اللون، يوجد لون نشط حاليًا بنفس الاسم '{bike_color.name}'")
    db.refresh(bike_color)
    audit_crud.log_action(db, "restore", "bike_color", bike_color.id, current_user_id, entity_label=bike_color.name)
    return bike_color