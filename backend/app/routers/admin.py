from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/dashboard/")
def get_dashboard(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)

@router.get("/chassis/{chassis_number}")
def get_chassis_history(chassis_number: str, db: Session = Depends(get_db)):
    records = db.query(models.AssemblyRecord).filter(models.AssemblyRecord.chassis_number == chassis_number).all()
    sale = db.query(models.Sale).filter(models.Sale.chassis_number == chassis_number).first()
    faults = db.query(models.Fault).filter(models.Fault.chassis_number == chassis_number).all()
    return {"assembly_records": records, "sale": sale, "faults": faults}

@router.post("/sales/")
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db)):
    # Check if already sold
    existing = db.query(models.Sale).filter(models.Sale.chassis_number == sale.chassis_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="هذه الدراجة مباعة مسبقاً")
    return crud.create_sale(db, sale)