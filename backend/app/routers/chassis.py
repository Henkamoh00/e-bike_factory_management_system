from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, models
from ..security import require_any_tab

router = APIRouter(prefix="/api/chassis", tags=["chassis"])

# 🛡️ بيانات الهياكل مشتركة بين 3 تبويبات (الورشة/المبيعات/الأعطال)
# لذا يكفي امتلاك أيٍّ منها للوصول، بدل تبويب واحد محدد
can_view_chassis = require_any_tab("assembly", "sales", "faults")

@router.get("/summary/")
def get_chassis_summary_list(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    return crud.get_chassis_summary(db)

@router.get("/available/")
def get_available_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    return crud.get_available_chassis(db)

@router.get("/all/")
def get_all_chassis_list(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    return crud.get_all_chassis_numbers(db)

@router.get("/{chassis_number}/")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_chassis)):
    history = crud.get_full_chassis_history(db, chassis_number)
    if not history["assembly_history"] and not history["sales"] and not history["faults"]:
        raise HTTPException(status_code=404, detail="لم يتم العثور على هذا الهيكل")
    return history