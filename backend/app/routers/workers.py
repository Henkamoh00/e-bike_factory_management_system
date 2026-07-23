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


@router.put("/{worker_id}/")
def update_worker(worker_id: int, worker: schemas.WorkerUpdate, db: Session = Depends(get_db)):
    try:
        return workshop_crud.update_worker(db, worker_id, worker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{worker_id}/")
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    try:
        workshop_crud.soft_delete_worker(db, worker_id)
        return {"message": "تم حذف العامل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_workers(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    return crud.bulk_soft_delete_workers(db, payload.ids)