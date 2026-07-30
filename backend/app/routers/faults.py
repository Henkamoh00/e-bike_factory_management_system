from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas, models
from ..security import get_current_user

router = APIRouter(prefix="/api/faults", tags=["faults"])

@router.post("/", response_model=schemas.FaultResponse)
def create_fault(fault: schemas.FaultCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_fault = crud.create_fault(db, fault, current_user.id)
    return crud._attach_fault_extras(db, [db_fault])[0]


@router.get("/", response_model=List[schemas.FaultResponse])
def get_all_faults(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """عرض كل الأعطال (معلقة، مصلَحة، وملغاة)"""
    return crud.get_all_faults(db, skip=skip, limit=limit)


@router.post("/{fault_id}/repair/", response_model=schemas.FaultRepairResponse)
def repair_fault(fault_id: int, repair: schemas.FaultRepairCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        db_repair = crud.create_fault_repair(db, fault_id, repair, current_user.id)
        db_repair.recorded_by_username = current_user.username
        return db_repair
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{fault_id}/cancel/", response_model=schemas.FaultResponse)
def cancel_fault(fault_id: int, payload: schemas.FaultCancel, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """إلغاء عطل (لا يُحذف، يبقى ظاهراً بالسجل مع علامة إلغاء وسبب)"""
    try:
        fault = crud.cancel_fault(db, fault_id, payload, current_user.id)
        return crud._attach_fault_extras(db, [fault])[0]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{fault_id}/suggested-worker/")
def suggested_worker(fault_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    suggestion = crud.get_suggested_worker_for_fault(db, fault_id)
    if not suggestion:
        return {"worker_id": None, "worker_name": None}
    return suggestion


@router.post("/bulk-cancel/", response_model=schemas.BulkActionResult)
def bulk_cancel_faults(payload: schemas.BulkCancel, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        return crud.bulk_cancel_faults(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-repair/", response_model=schemas.BulkActionResult)
def bulk_repair_faults(ids: schemas.BulkIds, worker_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.bulk_mark_faults_fixed(db, ids.ids, worker_name, current_user.id)