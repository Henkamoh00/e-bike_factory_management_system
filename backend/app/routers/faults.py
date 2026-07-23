from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas

router = APIRouter(prefix="/api/faults", tags=["faults"])

@router.post("/", response_model=schemas.FaultResponse)
def create_fault(fault: schemas.FaultCreate, db: Session = Depends(get_db)):
    return crud.create_fault(db, fault)


@router.get("/", response_model=List[schemas.FaultResponse])
def get_all_faults(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """عرض كل الأعطال (معلقة، مصلَحة، وملغاة)"""
    return crud.get_all_faults(db, skip=skip, limit=limit)


@router.post("/{fault_id}/repair/", response_model=schemas.FaultRepairResponse)
def repair_fault(fault_id: int, repair: schemas.FaultRepairCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_fault_repair(db, fault_id, repair)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{fault_id}/cancel/", response_model=schemas.FaultResponse)
def cancel_fault(fault_id: int, payload: schemas.FaultCancel, db: Session = Depends(get_db)):
    """إلغاء عطل (لا يُحذف، يبقى ظاهراً بالسجل مع علامة إلغاء وسبب)"""
    try:
        fault = crud.cancel_fault(db, fault_id, payload)
        return crud._attach_fault_extras(db, [fault])[0]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{fault_id}/suggested-worker/")
def suggested_worker(fault_id: int, db: Session = Depends(get_db)):
    suggestion = crud.get_suggested_worker_for_fault(db, fault_id)
    if not suggestion:
        return {"worker_id": None, "worker_name": None}
    return suggestion