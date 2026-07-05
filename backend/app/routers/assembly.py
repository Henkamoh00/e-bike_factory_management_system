from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, workshop_crud

router = APIRouter(prefix="/api/assembly", tags=["assembly"])

@router.post("/record", response_model=schemas.AssemblyResponse)
def create_assembly_record(
    assembly: schemas.AssemblyCreate,
    force: bool = Query(default=False, description="تجاوز تحذير العامل المختلف بعد تأكيد المسؤول"),
    db: Session = Depends(get_db)
):
    try:
        record = workshop_crud.create_assembly_record(db=db, assembly=assembly, force=force)
        return record
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @router.get("/records", response_model=List[schemas.AssemblyResponse])
# def get_records(db: Session = Depends(get_db)):
#     records = workshop_crud.get_assembly_records(db)
#     for record in records:
#         if record.worker:
#             record.worker_name = record.worker.name
#     return records