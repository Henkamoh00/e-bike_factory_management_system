from pydantic import BaseModel
from datetime import datetime
from .models import AssemblyStage


# ====================== WORKER ======================
class WorkerBase(BaseModel):
    name: str

class WorkerCreate(BaseModel):
    name: str
    phone: str | None = None
 
class WorkerUpdate(BaseModel):
    name: str | None = None
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

# ====================== BIKE TYPE / COLOR ======================
class BikeTypeCreate(BaseModel):
    name: str

class BikeTypeUpdate(BaseModel):
    name: str | None = None

class BikeTypeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class BikeColorCreate(BaseModel):
    name: str

class BikeColorUpdate(BaseModel):
    name: str | None = None

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
    bike_type_name: str | None = None
    bike_color_name: str | None = None
    force: bool = False

class AssemblyResponse(BaseModel):
    id: int
    chassis_number: str
    worker_id: int
    worker_name: str | None = None
    stage: str
    bike_type_name: str | None = None
    bike_color_name: str | None = None
    timestamp: datetime
    recorded_by_username: str | None = None   # 👈 جديد

    class Config:
        from_attributes = True


# ====================== CUSTOMER ======================
class CustomerBase(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    
class Customer(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ====================== SALE ======================
class SaleCreate(BaseModel):
    chassis_number: str
    customer_id: int
    notes: str | None = None
    sale_date: datetime | None = None

class SaleCancel(BaseModel):
    reason: str | None = None
    confirm_no_reason: bool = False

class SaleResponse(BaseModel):
    id: int
    chassis_number: str
    customer_id: int
    customer_name: str | None = None
    sale_date: datetime
    notes: str | None = None
    status: str = "active"
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    created_by_username: str | None = None     # 👈 جديد
    cancelled_by_username: str | None = None    # 👈 جديد

    class Config:
        from_attributes = True


# ====================== FAULT ======================
class FaultCreate(BaseModel):
    chassis_number: str
    description: str
    related_stage: AssemblyStage | None = None
    status: str | None = "pending"

class FaultCancel(BaseModel):
    reason: str | None = None
    confirm_no_reason: bool = False

class FaultRepairCreate(BaseModel):
    worker_name: str
    notes: str | None = None

class FaultRepairResponse(BaseModel):
    id: int
    fault_id: int
    worker_id: int
    worker_name: str | None = None
    repair_date: datetime
    notes: str | None = None
    recorded_by_username: str | None = None   # 👈 جديد

    class Config:
        from_attributes = True

class FaultResponse(BaseModel):
    id: int
    chassis_number: str
    description: str
    related_stage: str | None = None
    responsible_worker_name: str | None = None
    reported_date: datetime
    status: str
    resolved_at: datetime | None = None
    cancel_reason: str | None = None
    repairs: list[FaultRepairResponse] = []
    reported_by_username: str | None = None    # 👈 جديد
    cancelled_by_username: str | None = None    # 👈 جديد

    class Config:
        from_attributes = True


# ====================== BULK ACTIONS ======================
class BulkIds(BaseModel):
    ids: list[int]

class BulkCancel(BaseModel):
    ids: list[int]
    reason: str | None = None
    confirm_no_reason: bool = False

class BulkActionResult(BaseModel):
    success_count: int
    failed_ids: list[int] = []
    message: str


# ====================== DASHBOARD & HISTORY ======================
class DashboardStats(BaseModel):
    total_chassis: int
    completed: int
    in_progress: int
    sold: int
    pending_faults: int = 0

class ChassisHistoryResponse(BaseModel):
    chassis_number: str
    assembly_history: list[AssemblyResponse]
    sales: list[SaleResponse] = []
    faults: list[FaultResponse]

    class Config:
        from_attributes = True


# ====================== RESPONSE MODELS ======================
class ResponseMessage(BaseModel):
    message: str
    status: str = "success"


# ====================== ROLES ======================
# القائمة المرجعية الوحيدة لمعرّفات التبويبات المتاحة في لوحة الإدارة
# ⚠️ يجب أن تبقى متطابقة تمامًا مع TAB_DEFINITIONS في useTabPermissions.js بالفرونت إند
ALL_TAB_IDS = ["stats", "users", "settings", "assembly", "sales", "faults", "workers", "customers"]


class RoleCreate(BaseModel):
    name: str
    label: str
    description: str | None = None
    allowed_tabs: list[str] = []

class RoleUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    allowed_tabs: list[str] | None = None

class RoleResponse(BaseModel):
    id: int
    name: str
    label: str
    description: str | None = None
    is_system: bool
    allowed_tabs: list[str] = []
    users_count: int = 0

    class Config:
        from_attributes = True


# ====================== AUTH / USERS ======================
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str = "operator"

class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role: str
    role_label: str | None = None
    allowed_tabs: list[str] = []
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse