from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, workshop_crud, models

router = APIRouter(prefix="/api/workers", tags=["workers"])

@router.get("/simple/")
def get_workers(db: Session = Depends(get_db)):
    workers = workshop_crud.get_workers(db)
    return [{"id": w.id, "name": w.name} for w in workers]

@router.get("/")
def get_workers_full(db: Session = Depends(get_db)):
    return crud.get_workers_with_records(db)
 
 
@router.post("/")
def create_worker(worker: schemas.WorkerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Worker).filter(models.Worker.name == worker.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العامل موجود مسبقاً")
    return workshop_crud.get_or_create_worker(db, worker.name)