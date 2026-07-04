from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import workshop_crud, crud, schemas, models

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


# ====================== بحث عن الهيكل ======================
@router.get("/chassis/all")
def get_all_chassis_list(db: Session = Depends(get_db)):
    return crud.get_all_chassis_numbers(db)

@router.get("/chassis/available")
def get_available_chassis_list(db: Session = Depends(get_db)):
    return crud.get_available_chassis(db)

@router.get("/chassis/summary")
def get_chassis_summary_list(db: Session = Depends(get_db)):
    return crud.get_chassis_summary(db)

@router.get("/chassis/{chassis_number}")
def get_full_chassis_info(chassis_number: str, db: Session = Depends(get_db)):
    return crud.get_full_chassis_history(db, chassis_number)


# ── العمال ──────────────────────────────────────────────────────────────────
@router.get("/workers/")
def get_workers(db: Session = Depends(get_db)):
    return crud.get_workers_with_records(db)
 
 
@router.post("/workers/")
def create_worker(worker: schemas.WorkerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Worker).filter(models.Worker.name == worker.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العامل موجود مسبقاً")
    return workshop_crud.get_or_create_worker(db, worker.name)
 
 
# ── العملاء ──────────────────────────────────────────────────────────────────
@router.get("/customers/")
def get_customers(db: Session = Depends(get_db)):
    return crud.get_customers_with_sales(db)
 
 
@router.post("/customers/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.name == customer.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return crud.create_customer(db, customer)