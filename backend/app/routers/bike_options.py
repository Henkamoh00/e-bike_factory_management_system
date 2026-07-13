from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, workshop_crud

router = APIRouter(prefix="/api", tags=["bike-options"])


@router.get("/bike-types")
def get_bike_types(db: Session = Depends(get_db)):
    types = workshop_crud.get_bike_types(db)
    return [{"id": t.id, "name": t.name} for t in types]


@router.post("/bike-types")
def create_bike_type(data: schemas.BikeTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(models.BikeType).filter(models.BikeType.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="نوع الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_type(db, data.name)


@router.get("/bike-colors")
def get_bike_colors(db: Session = Depends(get_db)):
    colors = workshop_crud.get_bike_colors(db)
    return [{"id": c.id, "name": c.name} for c in colors]


@router.post("/bike-colors")
def create_bike_color(data: schemas.BikeColorCreate, db: Session = Depends(get_db)):
    existing = db.query(models.BikeColor).filter(models.BikeColor.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="لون الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_color(db, data.name)