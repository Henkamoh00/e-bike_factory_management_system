from pydantic import BaseModel, model_validator, ConfigDict
from datetime import datetime
from decimal import Decimal
from .models import AssemblyStage
from pydantic import field_validator


_SKIP_STRIP_FIELDS = {"password", "hashed_password"}

class StrippedBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _strip_string_fields(cls, data):
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, str) and key not in _SKIP_STRIP_FIELDS:
                    cleaned[key] = value.strip()
                else:
                    cleaned[key] = value
            return cleaned
        return data


MIN_PASSWORD_LENGTH = 8

def _validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LENGTH} أحرف على الأقل")
    return value

# ====================== WORKER ======================
class WorkerBase(BaseModel):
    name: str

class WorkerCreate(StrippedBaseModel):
    name: str
    phone: str | None = None

class WorkerUpdate(StrippedBaseModel):
    name: str | None = None
    phone: str | None = None

class WorkerResponse(BaseModel):
    id: int
    name: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class Worker(WorkerBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ====================== BIKE TYPE / COLOR ======================
class BikeTypeCreate(StrippedBaseModel):
    name: str
    default_price: Decimal | None = None

class BikeTypeUpdate(StrippedBaseModel):
    name: str | None = None
    default_price: Decimal | None = None

class BikeTypeResponse(BaseModel):
    id: int
    name: str
    default_price: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class BikeColorCreate(StrippedBaseModel):
    name: str

class BikeColorUpdate(StrippedBaseModel):
    name: str | None = None

class BikeColorResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# ====================== ASSEMBLY ======================
class AssemblyCreate(StrippedBaseModel):
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
    recorded_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== CUSTOMER ======================
class CustomerBase(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None

class CustomerCreate(StrippedBaseModel, CustomerBase):
    pass

class CustomerUpdate(StrippedBaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None

class Customer(CustomerBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ====================== سجل بيع الهيكل (🆕 مبني على نظام الفوترة) ======================
# 🛡️ حلّت محل SaleResponse القديمة بعد حذف نظام sales نهائيًا. تُبنى بيانات
# هذا النموذج من bند فاتورة (InvoiceItem) + الفاتورة + سجل الإرجاع إن وُجد،
# راجع chassis_crud.get_full_chassis_history لمصدر البيانات الفعلي.
class ChassisSaleHistoryItem(BaseModel):
    id: int
    invoice_number: str
    customer_id: int
    customer_name: str | None = None
    sale_date: datetime
    notes: str | None = None
    status: str = "active"
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    return_notes: str | None = None
    created_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== FAULT ======================
class FaultCreate(StrippedBaseModel):
    chassis_number: str
    description: str
    related_stage: AssemblyStage | None = None
    status: str | None = "pending"

class FaultCancel(StrippedBaseModel):
    reason: str | None = None
    confirm_no_reason: bool = False

class FaultRepairCreate(StrippedBaseModel):
    worker_name: str
    notes: str | None = None

class FaultRepairResponse(BaseModel):
    id: int
    fault_id: int
    worker_id: int
    worker_name: str | None = None
    repair_date: datetime
    notes: str | None = None
    recorded_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)

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
    reported_by_username: str | None = None
    cancelled_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== BULK ACTIONS ======================
class BulkIds(StrippedBaseModel):
    ids: list[int]

class BulkCancel(StrippedBaseModel):
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
    sales: list[ChassisSaleHistoryItem] = []
    faults: list[FaultResponse]

    model_config = ConfigDict(from_attributes=True)


# ====================== RESPONSE MODELS ======================
class ResponseMessage(BaseModel):
    message: str
    status: str = "success"


# ====================== ROLES ======================
ALL_TAB_IDS = ["stats", "users", "settings", "assembly", "invoices", "faults", "workers", "customers", "logs", "archive"]


class RoleCreate(StrippedBaseModel):
    name: str
    label: str
    description: str | None = None
    allowed_tabs: list[str] = []

class RoleUpdate(StrippedBaseModel):
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

    model_config = ConfigDict(from_attributes=True)


# ====================== AUTH / USERS ======================
class UserCreate(StrippedBaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str = "operator"

    @field_validator("password")
    @classmethod
    def _check_password(cls, v):
        return _validate_password_strength(v)

class UserUpdate(StrippedBaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v):
        if v is None:
            return v
        return _validate_password_strength(v)

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

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(StrippedBaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ====================== AUDIT LOG ======================
class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int | None = None
    entity_label: str | None = None
    details: str | None = None
    user_id: int | None = None
    username: str | None = None
    user_full_name: str | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


# ====================== ARCHIVE ======================
class ArchivedWorkerResponse(BaseModel):
    id: int
    name: str
    phone: str | None = None
    deleted_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ArchivedUserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role_label: str | None = None
    deleted_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ArchivedCustomerResponse(BaseModel):
    id: int
    name: str
    phone: str | None = None
    address: str | None = None
    deleted_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ArchivedBikeOptionResponse(BaseModel):
    id: int
    name: str
    deleted_by_username: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ====================== PAGINATION ======================
MAX_PAGE_LIMIT = 100
DEFAULT_PAGE_LIMIT = 20


class PaginatedWorkers(BaseModel):
    items: list[dict]
    total: int

class PaginatedCustomers(BaseModel):
    items: list[dict]
    total: int

class PaginatedBikeTypes(BaseModel):
    items: list[dict]
    total: int

class PaginatedBikeColors(BaseModel):
    items: list[dict]
    total: int

class PaginatedUsers(BaseModel):
    items: list[UserResponse]
    total: int


class WorkerSimpleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CustomerSimpleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedFaults(BaseModel):
    items: list[FaultResponse]
    total: int

class PaginatedChassisSummary(BaseModel):
    items: list[dict]
    total: int

class PaginatedArchivedWorkers(BaseModel):
    items: list[ArchivedWorkerResponse]
    total: int

class PaginatedArchivedCustomers(BaseModel):
    items: list[ArchivedCustomerResponse]
    total: int

class PaginatedArchivedBikeOptions(BaseModel):
    items: list[ArchivedBikeOptionResponse]
    total: int

class PaginatedArchivedUsers(BaseModel):
    items: list[ArchivedUserResponse]
    total: int