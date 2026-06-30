from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import crud, schemas

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


# ====================== الإحصائيات ======================
@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)


# ====================== المبيعات ======================
@router.post("/sales/", response_model=schemas.SaleResponse)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_sale(db, sale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sales/", response_model=List[schemas.SaleResponse])
def get_all_sales(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """عرض كل المبيعات"""
    return crud.get_sales(db, skip=skip, limit=limit)


# ====================== الأعطال ======================
@router.post("/faults/", response_model=schemas.FaultResponse)
def create_fault(fault: schemas.FaultCreate, db: Session = Depends(get_db)):
    return crud.create_fault(db, fault)


@router.get("/faults/", response_model=List[schemas.FaultResponse])
def get_all_faults(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """عرض كل الأعطال"""
    return crud.get_all_faults(db, skip=skip, limit=limit)


# ====================== بحث كامل ======================
@router.get("/chassis/{chassis_number}")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db)):
    return crud.get_full_chassis_history(db, chassis_number)