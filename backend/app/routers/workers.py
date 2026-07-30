from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, workshop_crud, models
from ..security import get_current_user, require_roles

router = APIRouter(prefix="/api/workers", tags=["workers"])

admin_or_supervisor = require_roles(models.UserRole.ADMIN, models.UserRole.SUPERVISOR)


@router.get("/simple/")
def get_workers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    workers = workshop_crud.get_workers(db)
    return [{"id": w.id, "name": w.name} for w in workers]

@router.get("/")
def get_workers_full(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_workers_with_records(db)


@router.post("/")
def create_worker(worker: schemas.WorkerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    existing = db.query(models.Worker).filter(models.Worker.name == worker.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العامل موجود مسبقاً")
    return workshop_crud.get_or_create_worker(db, worker.name, current_user.id)


@router.put("/{worker_id}/")
def update_worker(worker_id: int, worker: schemas.WorkerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        return workshop_crud.update_worker(db, worker_id, worker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{worker_id}/")
def delete_worker(worker_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        workshop_crud.soft_delete_worker(db, worker_id, current_user.id)
        return {"message": "تم حذف العامل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_workers(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    return crud.bulk_soft_delete_workers(db, payload.ids, current_user.id)