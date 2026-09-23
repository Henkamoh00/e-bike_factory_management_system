from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models as app_models
from app.security import require_tab
from .. import schemas, inventory_crud

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

can_access_inventory = require_tab("inventory")


# ====================== القطع ======================
@router.get("/parts/simple/")
def search_parts(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    parts = inventory_crud.search_parts_simple(db, q=q, limit=limit)
    return [{"id": p.id, "name": p.name, "unit": p.unit} for p in parts]


@router.get("/parts/", response_model=schemas.PaginatedParts)
def get_parts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    items, total = inventory_crud.get_parts(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


@router.post("/parts/", response_model=schemas.PartResponse)
def create_part(
    data: schemas.PartCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.create_part(db, data, current_user.id)


@router.put("/parts/{part_id}/", response_model=schemas.PartResponse)
def update_part(
    part_id: int,
    data: schemas.PartUpdate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.update_part(db, part_id, data, current_user.id)


@router.delete("/parts/{part_id}/")
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    inventory_crud.soft_delete_part(db, part_id, current_user.id)
    return {"message": "تم حذف القطعة بنجاح", "status": "success"}


@router.post("/parts/{part_id}/restore/", response_model=schemas.PartResponse)
def restore_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.restore_part(db, part_id, current_user.id)


# ====================== قائمة الطلب (قطع نافدة) ======================
@router.get("/reorder-list/", response_model=list[schemas.PartResponse])
def get_reorder_list(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.get_reorder_list(db)


@router.post("/parts/{part_id}/reorder/", response_model=schemas.PartResponse)
def toggle_reorder(
    part_id: int,
    data: schemas.ReorderToggle,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.toggle_reorder(db, part_id, data.flagged, current_user.id)


# ====================== الموردون ======================
@router.get("/suppliers/simple/")
def search_suppliers(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    suppliers = inventory_crud.search_suppliers_simple(db, q=q, limit=limit)
    return [{"id": s.id, "name": s.name} for s in suppliers]


@router.post("/suppliers/", response_model=schemas.SupplierResponse)
def create_supplier(
    data: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.create_supplier(db, data, current_user.id)


# ====================== حركات المخزون ======================
@router.get("/movements/", response_model=schemas.PaginatedStockMovements)
def get_movements(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    part_id: int | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    items, total = inventory_crud.get_movements(
        db, skip=skip, limit=limit, part_id=part_id, movement_type=movement_type
    )
    return {"items": items, "total": total}


@router.post("/movements/", response_model=schemas.StockMovementResponse)
def create_movement(
    data: schemas.StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_inventory)
):
    return inventory_crud.record_movement(db, data, current_user.id)
