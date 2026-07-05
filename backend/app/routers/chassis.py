from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud

router = APIRouter(prefix="/api/chassis", tags=["chassis"])

@router.get("/summary")
def get_chassis_summary_list(db: Session = Depends(get_db)):
    return crud.get_chassis_summary(db)

@router.get("/available")
def get_available_chassis_list(db: Session = Depends(get_db)):
    return crud.get_available_chassis(db)

@router.get("/all")
def get_all_chassis_list(db: Session = Depends(get_db)):
    return crud.get_all_chassis_numbers(db)

@router.get("/{chassis_number}")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db)):
    history = crud.get_full_chassis_history(db, chassis_number)
    if not history["assembly_history"] and not history["sale"] and not history["faults"]:
        raise HTTPException(status_code=404, detail="لم يتم العثور على هذا الهيكل")
    return history