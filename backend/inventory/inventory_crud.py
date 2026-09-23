from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from fastapi import HTTPException
from app import audit_crud
from . import models, schemas


# ====================== القطع ======================
def create_part(db: Session, data: schemas.PartCreate, current_user_id: int):
    part = models.Part(name=data.name, unit=data.unit, created_by_id=current_user_id)
    db.add(part)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="القطعة موجودة مسبقاً")
    db.refresh(part)
    audit_crud.log_action(db, "create", "part", part.id, current_user_id, entity_label=part.name)
    return part


def _get_part_for_update(db: Session, part_id: int) -> models.Part:
    part = (
        db.query(models.Part)
        .filter(models.Part.id == part_id, models.Part.is_deleted.is_(False))
        .with_for_update()
        .first()
    )
    if not part:
        raise HTTPException(status_code=404, detail="القطعة غير موجودة")
    return part


def update_part(db: Session, part_id: int, data: schemas.PartUpdate, current_user_id: int):
    part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="القطعة غير موجودة")
    if part.is_deleted:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل قطعة مؤرشفة، يجب استعادتها أولاً")

    if data.name is not None:
        part.name = data.name
    if data.unit is not None:
        part.unit = data.unit

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"يوجد قطعة أخرى بنفس الاسم '{data.name}' مسبقاً")
    db.refresh(part)
    audit_crud.log_action(db, "update", "part", part.id, current_user_id, entity_label=part.name)
    return part


def soft_delete_part(db: Session, part_id: int, current_user_id: int):
    part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="القطعة غير موجودة")
    part.is_deleted = True
    part.deleted_by_id = current_user_id
    db.commit()
    audit_crud.log_action(db, "delete", "part", part.id, current_user_id, entity_label=part.name)
    return part


def restore_part(db: Session, part_id: int, current_user_id: int):
    part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="القطعة غير موجودة")
    if not part.is_deleted:
        raise HTTPException(status_code=400, detail="القطعة غير مؤرشفة أصلاً")

    duplicate = db.query(models.Part).filter(
        models.Part.name == part.name, models.Part.is_deleted.is_(False), models.Part.id != part.id
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=f"لا يمكن استعادة القطعة، يوجد قطعة نشطة حاليًا بنفس الاسم '{part.name}'"
        )

    part.is_deleted = False
    part.deleted_by_id = None
    db.commit()
    audit_crud.log_action(db, "restore", "part", part.id, current_user_id, entity_label=part.name)
    return part


def get_parts(db: Session, skip: int = 0, limit: int = 20, search: str | None = None):
    query = db.query(models.Part).filter(models.Part.is_deleted.is_(False))
    if search:
        query = query.filter(models.Part.name.ilike(f"%{search}%"))
    total = query.count()
    items = query.order_by(models.Part.name).offset(skip).limit(limit).all()
    return items, total


def search_parts_simple(db: Session, q: str | None = None, limit: int = 20):
    query = db.query(models.Part).filter(models.Part.is_deleted.is_(False))
    if q:
        query = query.filter(models.Part.name.ilike(f"%{q}%"))
    return query.order_by(models.Part.name).limit(limit).all()


def get_reorder_list(db: Session):
    return (
        db.query(models.Part)
        .filter(models.Part.is_deleted.is_(False), models.Part.flagged_for_reorder.is_(True))
        .order_by(models.Part.name)
        .all()
    )


def toggle_reorder(db: Session, part_id: int, flagged: bool, current_user_id: int):
    part = db.query(models.Part).filter(models.Part.id == part_id, models.Part.is_deleted.is_(False)).first()
    if not part:
        raise HTTPException(status_code=404, detail="القطعة غير موجودة")
    part.flagged_for_reorder = flagged
    db.commit()
    db.refresh(part)
    audit_crud.log_action(
        db, "update", "part", part.id, current_user_id,
        entity_label=f"{part.name} — {'أُضيفت لقائمة الطلب' if flagged else 'أُزيلت من قائمة الطلب'}"
    )
    return part


# ====================== الموردون ======================
def get_or_create_supplier(db: Session, name: str, current_user_id: int | None = None) -> models.Supplier:
    """نفس نمط get_or_create_worker: يُنشئ المورّد تلقائيًا لو لم يكن موجودًا"""
    supplier = db.query(models.Supplier).filter(models.Supplier.name == name).first()
    if not supplier:
        supplier = models.Supplier(name=name, created_by_id=current_user_id)
        db.add(supplier)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            supplier = db.query(models.Supplier).filter(models.Supplier.name == name).first()
            if not supplier:
                raise HTTPException(status_code=400, detail="تعذر إنشاء المورّد، يرجى المحاولة مجدداً")
            return supplier
        db.refresh(supplier)
        audit_crud.log_action(db, "create", "supplier", supplier.id, current_user_id, entity_label=supplier.name)
    elif supplier.is_deleted:
        supplier.is_deleted = False
        supplier.deleted_by_id = None
        db.commit()
        db.refresh(supplier)
    return supplier


def create_supplier(db: Session, data: schemas.SupplierCreate, current_user_id: int):
    existing = db.query(models.Supplier).filter(
        models.Supplier.name == data.name, models.Supplier.is_deleted.is_(False)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="المورّد موجود مسبقاً")
    return get_or_create_supplier(db, data.name, current_user_id)


def search_suppliers_simple(db: Session, q: str | None = None, limit: int = 20):
    query = db.query(models.Supplier).filter(models.Supplier.is_deleted.is_(False))
    if q:
        query = query.filter(models.Supplier.name.ilike(f"%{q}%"))
    return query.order_by(models.Supplier.name).limit(limit).all()


# ====================== حركات المخزون ======================
def record_movement(db: Session, data: schemas.StockMovementCreate, current_user_id: int):
    part = _get_part_for_update(db, data.part_id)

    if data.movement_type == "out":
        if data.quantity > part.current_stock:
            raise HTTPException(
                status_code=422,
                detail=f"⛔ الكمية المطلوب صرفها ({data.quantity}) أكبر من المتوفر حاليًا ({part.current_stock})"
            )
        new_balance = part.current_stock - data.quantity
    else:  # "in"
        new_balance = part.current_stock + data.quantity

    part.current_stock = new_balance

    # 🆕 السعر والمورّد لهما معنى فقط في حركات الوارد — يُتجاهلان صراحة في الصادر
    is_incoming = data.movement_type == "in"
    supplier_id = None
    if is_incoming and data.supplier_name:
        supplier = get_or_create_supplier(db, data.supplier_name, current_user_id)
        supplier_id = supplier.id

    movement = models.StockMovement(
        part_id=part.id,
        movement_type=data.movement_type,
        quantity=data.quantity,
        balance_after=new_balance,
        unit_price=data.unit_price if is_incoming else None,
        supplier_id=supplier_id,
        related_chassis_number=data.related_chassis_number,
        notes=data.notes,
        created_by_id=current_user_id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    db.refresh(part)

    label_action = "وارد إلى" if data.movement_type == "in" else "صادر من"
    audit_crud.log_action(
        db, "create", "stock_movement", movement.id, current_user_id,
        entity_label=f"{data.quantity} {part.unit} {label_action} {part.name}",
        details=data.notes
    )

    movement.part_name = part.name
    movement.supplier_name = movement.supplier.name if movement.supplier else None
    movement.created_by_username = movement.created_by.username if movement.created_by else None
    return movement


def _attach_movement_extras(movements):
    for m in movements:
        m.part_name = m.part.name if m.part else None
        m.supplier_name = m.supplier.name if m.supplier else None
        m.created_by_username = m.created_by.username if m.created_by else None
    return movements


def get_movements(db: Session, skip: int = 0, limit: int = 20, part_id: int | None = None,
                   movement_type: str | None = None):
    query = db.query(models.StockMovement).options(
        joinedload(models.StockMovement.part),
        joinedload(models.StockMovement.supplier),
        joinedload(models.StockMovement.created_by),
    )
    if part_id:
        query = query.filter(models.StockMovement.part_id == part_id)
    if movement_type:
        query = query.filter(models.StockMovement.movement_type == movement_type)

    total = query.count()
    items = query.order_by(desc(models.StockMovement.created_at), desc(models.StockMovement.id)) \
        .offset(skip).limit(limit).all()
    return _attach_movement_extras(items), total
