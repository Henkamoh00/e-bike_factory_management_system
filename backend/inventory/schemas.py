from pydantic import BaseModel, ConfigDict, model_validator, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Literal


class StrippedBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _strip_string_fields(cls, data):
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, str):
                    cleaned[key] = value.strip()
                else:
                    cleaned[key] = value
            return cleaned
        return data


# ====================== القطعة ======================
class PartCreate(StrippedBaseModel):
    name: str
    unit: str


class PartUpdate(StrippedBaseModel):
    name: str | None = None
    unit: str | None = None


class PartResponse(BaseModel):
    id: int
    name: str
    unit: str
    current_stock: Decimal
    flagged_for_reorder: bool

    model_config = ConfigDict(from_attributes=True)


class PaginatedParts(BaseModel):
    items: list[PartResponse]
    total: int


class ReorderToggle(StrippedBaseModel):
    flagged: bool


# ====================== المورّد ======================
class SupplierCreate(StrippedBaseModel):
    name: str


class SupplierResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# ====================== حركة المخزون ======================
class StockMovementCreate(StrippedBaseModel):
    part_id: int
    movement_type: Literal["in", "out"]
    quantity: Decimal
    # 🆕 السعر (معنى له فقط عند movement_type == "in"؛ يُتجاهل صراحة في
    # حركات الصادر داخل inventory_crud.record_movement)
    unit_price: Decimal | None = None
    # 🆕 اسم المورّد كنص حر: يُحوَّل إلى معرّف عبر get-or-create تلقائيًا
    supplier_name: str | None = None
    related_chassis_number: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def _check_positive(cls, v):
        if v <= 0:
            raise ValueError("الكمية يجب أن تكون أكبر من صفر")
        return v

    @field_validator("unit_price")
    @classmethod
    def _check_price_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("السعر لا يمكن أن يكون بالسالب")
        return v


class StockMovementResponse(BaseModel):
    id: int
    part_id: int
    part_name: str | None = None
    movement_type: str
    quantity: Decimal
    balance_after: Decimal
    unit_price: Decimal | None = None
    supplier_name: str | None = None
    related_chassis_number: str | None = None
    notes: str | None = None
    created_by_username: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedStockMovements(BaseModel):
    items: list[StockMovementResponse]
    total: int
