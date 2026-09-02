from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
from sqlalchemy.orm import Session
from ..database import get_db
from .. import faults_crud, schemas, models
from ..security import require_tab
from ..rate_limit import limiter

router = APIRouter(prefix="/api/faults", tags=["faults"])

can_access_faults = require_tab("faults")

@router.post("/", response_model=schemas.FaultResponse)
def create_fault(fault: schemas.FaultCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_faults)):
    db_fault = faults_crud.create_fault(db, fault, current_user.id)
    return faults_crud._attach_fault_extras(db, [db_fault])[0]


@router.get("/", response_model=schemas.PaginatedFaults)
def get_all_faults(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    chassis_number: str | None = Query(default=None),
    status: str | None = Query(default=None),
    repaired_by: str | None = Query(default=None),
    responsible_worker: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_faults)
):
    """عرض الأعطال (معلقة، مصلَحة، وملغاة) مُصفَّحة ومُفلتَرة من السيرفر"""
    items, total = faults_crud.get_all_faults(
        db, skip=skip, limit=limit,
        chassis_number=chassis_number, status=status,
        repaired_by=repaired_by, responsible_worker=responsible_worker
    )
    return {"items": items, "total": total}


@router.post("/{fault_id}/repair/", response_model=schemas.FaultRepairResponse)
def repair_fault(fault_id: int, repair: schemas.FaultRepairCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_faults)):
    try:
        db_repair = faults_crud.create_fault_repair(db, fault_id, repair, current_user.id)
        db_repair.recorded_by_username = current_user.username
        return db_repair
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{fault_id}/cancel/", response_model=schemas.FaultResponse)
def cancel_fault(fault_id: int, payload: schemas.FaultCancel, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_faults)):
    try:
        fault = faults_crud.cancel_fault(db, fault_id, payload, current_user.id)
        return faults_crud._attach_fault_extras(db, [fault])[0]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{fault_id}/suggested-worker/")
def suggested_worker(fault_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_faults)):
    suggestion = faults_crud.get_suggested_worker_for_fault(db, fault_id)
    if not suggestion:
        return {"worker_id": None, "worker_name": None}
    return suggestion


# 🛡️🆕 حد على bulk-cancel
@router.post("/bulk-cancel/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour")
def bulk_cancel_faults(
    request: Request,
    payload: schemas.BulkCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_faults)
):
    try:
        return faults_crud.bulk_cancel_faults(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🛡️🆕 حد على bulk-repair
@router.post("/bulk-repair/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour")
def bulk_repair_faults(
    request: Request,
    ids: schemas.BulkIds,
    worker_name: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_faults)
):
    try:
        return faults_crud.bulk_mark_faults_fixed(db, ids.ids, worker_name, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))