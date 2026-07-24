from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, workshop_crud, crud

router = APIRouter(prefix="/api", tags=["bike-options"])


# ====================== BIKE TYPES ======================
@router.get("/bike-types/")
def get_bike_types(db: Session = Depends(get_db)):
    return crud.get_bike_types_with_usage(db)


@router.post("/bike-types/")
def create_bike_type(data: schemas.BikeTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(models.BikeType).filter(
        models.BikeType.name == data.name,
        models.BikeType.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="نوع الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_type(db, data.name)


@router.put("/bike-types/{type_id}/")
def update_bike_type(type_id: int, data: schemas.BikeTypeUpdate, db: Session = Depends(get_db)):
    try:
        return workshop_crud.update_bike_type(db, type_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-types/{type_id}/")
def delete_bike_type(type_id: int, db: Session = Depends(get_db)):
    try:
        workshop_crud.soft_delete_bike_type(db, type_id)
        return {"message": "تم حذف نوع الدراجة بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-types/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_types(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    return crud.bulk_soft_delete_bike_types(db, payload.ids)


# ====================== BIKE COLORS ======================
@router.get("/bike-colors/")
def get_bike_colors(db: Session = Depends(get_db)):
    return crud.get_bike_colors_with_usage(db)


@router.post("/bike-colors/")
def create_bike_color(data: schemas.BikeColorCreate, db: Session = Depends(get_db)):
    existing = db.query(models.BikeColor).filter(
        models.BikeColor.name == data.name,
        models.BikeColor.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="لون الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_color(db, data.name)


@router.put("/bike-colors/{color_id}/")
def update_bike_color(color_id: int, data: schemas.BikeColorUpdate, db: Session = Depends(get_db)):
    try:
        return workshop_crud.update_bike_color(db, color_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-colors/{color_id}/")
def delete_bike_color(color_id: int, db: Session = Depends(get_db)):
    try:
        workshop_crud.soft_delete_bike_color(db, color_id)
        return {"message": "تم حذف لون الدراجة بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-colors/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_colors(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    return crud.bulk_soft_delete_bike_colors(db, payload.ids)