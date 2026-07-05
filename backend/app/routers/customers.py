from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, models

router = APIRouter(prefix="/api/customers", tags=["customers"])

@router.get("/")
def get_customers(db: Session = Depends(get_db)):
    return crud.get_customers_with_sales(db)
 
 
@router.post("/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.name == customer.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return crud.create_customer(db, customer)