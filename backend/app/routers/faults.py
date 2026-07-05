from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas

router = APIRouter(prefix="/api/faults", tags=["faults"])

@router.post("/", response_model=schemas.FaultResponse)
def create_fault(fault: schemas.FaultCreate, db: Session = Depends(get_db)):
    return crud.create_fault(db, fault)


@router.get("/", response_model=List[schemas.FaultResponse])
def get_all_faults(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """عرض كل الأعطال"""
    return crud.get_all_faults(db, skip=skip, limit=limit)
