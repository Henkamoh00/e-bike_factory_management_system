from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, models
from ..security import get_current_user

router = APIRouter(prefix="/api/chassis", tags=["chassis"])

# القراءة متاحة لكل مستخدم مسجّل دخول (admin / supervisor / operator)
@router.get("/summary/")
def get_chassis_summary_list(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_chassis_summary(db)

@router.get("/available/")
def get_available_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_available_chassis(db)

@router.get("/all/")
def get_all_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_all_chassis_numbers(db)

@router.get("/{chassis_number}/")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    history = crud.get_full_chassis_history(db, chassis_number)
    if not history["assembly_history"] and not history["sales"] and not history["faults"]:
        raise HTTPException(status_code=404, detail="لم يتم العثور على هذا الهيكل")
    return history