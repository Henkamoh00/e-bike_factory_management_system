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
 
class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

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

# ====================== BIKE TYPE / COLOR ======================
class BikeTypeCreate(BaseModel):
    name: str

class BikeTypeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class BikeColorCreate(BaseModel):
    name: str

class BikeColorResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ====================== ASSEMBLY ======================
class AssemblyCreate(BaseModel):
    chassis_number: str
    worker_name: str
    stage: AssemblyStage
    bike_type_name: Optional[str] = None
    bike_color_name: Optional[str] = None
    force: bool = False

class AssemblyResponse(BaseModel):
    id: int
    chassis_number: str
    worker_id: int
    worker_name: Optional[str] = None
    stage: str
    bike_type_name: Optional[str] = None
    bike_color_name: Optional[str] = None
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

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
class Customer(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ====================== SALE ======================
class SaleCreate(BaseModel):
    chassis_number: str
    customer_id: int
    notes: Optional[str] = None
    sale_date: Optional[datetime] = None

class SaleCancel(BaseModel):
    reason: Optional[str] = None
    confirm_no_reason: bool = False

class SaleResponse(BaseModel):
    id: int
    chassis_number: str
    customer_id: int
    customer_name: Optional[str] = None
    sale_date: datetime
    notes: Optional[str] = None
    status: str = "active"
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ====================== FAULT ======================
class FaultCreate(BaseModel):
    chassis_number: str
    description: str
    related_stage: Optional[AssemblyStage] = None
    status: Optional[str] = "pending"

class FaultCancel(BaseModel):
    reason: Optional[str] = None
    confirm_no_reason: bool = False

class FaultRepairCreate(BaseModel):
    worker_name: str
    notes: Optional[str] = None

class FaultRepairResponse(BaseModel):
    id: int
    fault_id: int
    worker_id: int
    worker_name: Optional[str] = None
    repair_date: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class FaultResponse(BaseModel):
    id: int
    chassis_number: str
    description: str
    related_stage: Optional[str] = None
    responsible_worker_name: Optional[str] = None
    reported_date: datetime
    status: str
    resolved_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    repairs: List[FaultRepairResponse] = []

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
    sales: List[SaleResponse] = []
    faults: List[FaultResponse]

    class Config:
        from_attributes = True


# ====================== RESPONSE MODELS ======================
class ResponseMessage(BaseModel):
    message: str
    status: str = "success"