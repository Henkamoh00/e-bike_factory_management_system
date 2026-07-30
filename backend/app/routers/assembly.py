from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, workshop_crud, models
from ..security import get_current_user

router = APIRouter(prefix="/api/assembly", tags=["assembly"])

@router.post("/record/", response_model=schemas.AssemblyResponse)
def create_assembly_record(
    assembly: schemas.AssemblyCreate,
    force: bool = Query(default=False, description="تجاوز تحذير العامل المختلف بعد تأكيد المسؤول"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        record = workshop_crud.create_assembly_record(
            db=db,
            assembly=assembly,
            current_user_id=current_user.id,
            force=force,
        )
        if record.recorded_by:
            record.recorded_by_username = record.recorded_by.username
        return record
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))