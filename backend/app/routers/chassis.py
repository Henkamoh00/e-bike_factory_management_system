from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import chassis_crud, schemas, models
from ..security import require_any_tab

router = APIRouter(prefix="/api/chassis", tags=["chassis"])

can_view_chassis = require_any_tab("assembly", "sales", "faults")

@router.get("/summary/", response_model=schemas.PaginatedChassisSummary)
def get_chassis_summary_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    chassis_number: str | None = Query(default=None),
    status: str | None = Query(default=None),
    worker_name: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    bike_type: str | None = Query(default=None),
    bike_color: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_chassis)
):
    items, total = chassis_crud.get_chassis_summary(
        db, skip=skip, limit=limit,
        chassis_number=chassis_number, status=status,
        worker_name=worker_name, stage=stage,
        bike_type=bike_type, bike_color=bike_color
    )
    return {"items": items, "total": total}

@router.get("/available/")
def get_available_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    return chassis_crud.get_available_chassis(db)

@router.get("/all/")
def get_all_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    return chassis_crud.get_all_chassis_numbers(db)

@router.get("/{chassis_number}/")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    history = chassis_crud.get_full_chassis_history(db, chassis_number)
    if not history["assembly_history"] and not history["sales"] and not history["faults"]:
        raise HTTPException(status_code=404, detail="لم يتم العثور على هذا الهيكل")
    return history