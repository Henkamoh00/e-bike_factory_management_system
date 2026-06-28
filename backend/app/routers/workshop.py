from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud

router = APIRouter(
    prefix="/workshop",
    tags=["workshop"]
)


@router.post("/record", response_model=schemas.AssemblyResponse)
def create_assembly_record(
    assembly: schemas.AssemblyCreate, 
    force: bool = Query(default=False, description="تجاوز تحذير العامل المختلف بعد تأكيد المسؤول"),
    db: Session = Depends(get_db)
):
    try:
        record = crud.create_assembly_record(db=db, assembly=assembly, force=force)
        return record
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/records", response_model=List[schemas.AssemblyResponse])
def get_records(db: Session = Depends(get_db)):
    records = crud.get_assembly_records(db)
    # إضافة اسم العامل لكل سجل
    for record in records:
        if record.worker:
            record.worker_name = record.worker.name
    return records


@router.get("/history/{chassis_number}", response_model=schemas.ChassisHistoryResponse)
def get_chassis_history(chassis_number: str, db: Session = Depends(get_db)):
    history = crud.get_full_chassis_history(db, chassis_number)
    if not history["assembly_history"] and not history["sale"] and not history["faults"]:
        raise HTTPException(status_code=404, detail="لم يتم العثور على هذا الهيكل")
    return history