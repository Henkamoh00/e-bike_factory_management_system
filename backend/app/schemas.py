from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .models import AssemblyStage


# ====================== WORKER ======================
class WorkerBase(BaseModel):
    name: str

class WorkerCreate(BaseModel):
    name: str
    phone: str | None = None
 
class WorkerResponse(BaseModel):
    id: int
    name: str
    phone: str | None = None
 
    class Config:
        from_attributes = True
 

class Worker(WorkerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ====================== ASSEMBLY ======================
class AssemblyCreate(BaseModel):
    chassis_number: str
    worker_name: str
    stage: AssemblyStage
    force: bool = False

class AssemblyResponse(BaseModel):
    id: int
    chassis_number: str
    worker_id: int
    worker_name: Optional[str] = None
    stage: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ====================== CUSTOMER ======================
class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ====================== SALE ======================
class SaleCreate(BaseModel):
    chassis_number: str
    customer_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    sale_date: Optional[datetime] = None

class SaleResponse(BaseModel):
    id: int
    chassis_number: str
    customer_id: int
    customer_name: Optional[str] = None
    sale_date: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ====================== FAULT ======================
class FaultCreate(BaseModel):
    chassis_number: str
    description: str
    status: Optional[str] = "pending"

class FaultResponse(BaseModel):
    id: int
    chassis_number: str
    description: str
    worker_name: str | None = None
    reported_date: datetime
    status: str

    class Config:
        from_attributes = True


# ====================== DASHBOARD & HISTORY ======================
class DashboardStats(BaseModel):
    total_chassis: int
    completed: int
    in_progress: int
    sold: int
    pending_faults: int = 0

class ChassisHistoryResponse(BaseModel):
    chassis_number: str
    assembly_history: List[AssemblyResponse]
    sale: Optional[SaleResponse] = None
    faults: List[FaultResponse]

    class Config:
        from_attributes = True


# ====================== RESPONSE MODELS ======================
class ResponseMessage(BaseModel):
    message: str
    status: str = "success"