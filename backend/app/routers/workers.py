from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import reports_crud, schemas, workshop_crud, models
from ..security import get_current_user, require_tab

router = APIRouter(prefix="/api/workers", tags=["workers"])

can_manage_workers = require_tab("workers")
can_view_archive = require_tab("archive")


@router.get("/simple/")
def get_workers_simple(
    q: str | None = Query(default=None, description="بحث باسم العامل"),
    limit: int = Query(default=20, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    🆕 نقطة نهاية خفيفة مخصصة للقوائم المنسدلة (SearchableSelect)
    تدعم بحثًا ديناميكيًا بدل تحميل كل العمال دفعة واحدة.
    """
    workers = workshop_crud.search_workers_simple(db, q=q, limit=limit)
    return [{"id": w.id, "name": w.name} for w in workers]


@router.get("/", response_model=schemas.PaginatedWorkers)
def get_workers_full(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    search: str | None = Query(default=None, description="بحث باسم العامل"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    items, total = reports_crud.get_workers_with_records(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


@router.post("/")
def create_worker(worker: schemas.WorkerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.Worker).filter(
        models.Worker.name == worker.name,
        models.Worker.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="العامل موجود مسبقاً")
    return workshop_crud.get_or_create_worker(db, worker.name, current_user.id)


@router.put("/{worker_id}/")
def update_worker(worker_id: int, worker: schemas.WorkerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_workers)):
    try:
        return workshop_crud.update_worker(db, worker_id, worker, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{worker_id}/")
def delete_worker(worker_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_workers)):
    try:
        workshop_crud.soft_delete_worker(db, worker_id, current_user.id)
        return {"message": "تم حذف العامل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_workers(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_workers)):
    return reports_crud.bulk_soft_delete_workers(db, payload.ids, current_user.id)


@router.get("/archived/", response_model=schemas.PaginatedArchivedWorkers)
def get_archived_workers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_archive)
):
    items, total = workshop_crud.get_archived_workers(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/{worker_id}/restore/")
def restore_worker(worker_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.restore_worker(db, worker_id, current_user.id)
        return {"message": "تم استعادة العامل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))