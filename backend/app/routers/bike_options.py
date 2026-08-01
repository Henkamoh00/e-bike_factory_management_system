from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, workshop_crud, crud
from ..security import get_current_user, require_tab

router = APIRouter(prefix="/api", tags=["bike-options"])

can_view_archive = require_tab("archive")


# ====================== BIKE TYPES ======================
@router.get("/bike-types/")
def get_bike_types(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_bike_types_with_usage(db)


@router.post("/bike-types/")
def create_bike_type(data: schemas.BikeTypeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    existing = db.query(models.BikeType).filter(
        models.BikeType.name == data.name,
        models.BikeType.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="نوع الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_type(db, data.name, current_user.id)


@router.put("/bike-types/{type_id}/")
def update_bike_type(type_id: int, data: schemas.BikeTypeUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        return workshop_crud.update_bike_type(db, type_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-types/{type_id}/")
def delete_bike_type(type_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.soft_delete_bike_type(db, type_id, current_user.id)
        return {"message": "تم حذف نوع الدراجة بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-types/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_types(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    return crud.bulk_soft_delete_bike_types(db, payload.ids, current_user.id)


# ====================== BIKE COLORS ======================
@router.get("/bike-colors/")
def get_bike_colors(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_bike_colors_with_usage(db)


@router.post("/bike-colors/")
def create_bike_color(data: schemas.BikeColorCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    existing = db.query(models.BikeColor).filter(
        models.BikeColor.name == data.name,
        models.BikeColor.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="لون الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_color(db, data.name, current_user.id)


@router.put("/bike-colors/{color_id}/")
def update_bike_color(color_id: int, data: schemas.BikeColorUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        return workshop_crud.update_bike_color(db, color_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-colors/{color_id}/")
def delete_bike_color(color_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.soft_delete_bike_color(db, color_id, current_user.id)
        return {"message": "تم حذف لون الدراجة بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-colors/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_colors(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    return crud.bulk_soft_delete_bike_colors(db, payload.ids, current_user.id)


@router.get("/bike-types/archived/")
def get_archived_bike_types(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    return workshop_crud.get_archived_bike_types(db)


@router.post("/bike-types/{type_id}/restore/")
def restore_bike_type(type_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.restore_bike_type(db, type_id, current_user.id)
        return {"message": "تم استعادة النوع بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bike-colors/archived/")
def get_archived_bike_colors(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    return workshop_crud.get_archived_bike_colors(db)


@router.post("/bike-colors/{color_id}/restore/")
def restore_bike_color(color_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.restore_bike_color(db, color_id, current_user.id)
        return {"message": "تم استعادة اللون بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))