from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class AssemblyStage(str, enum.Enum):
    CHASSIS_ASSEMBLY = "تجميع_الهيكل"
    ELECTRICAL_COVER = "توصيل_الكهرباء_والغلاف"
    FINAL_ASSEMBLY = "تجميع_كامل"

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── تتبع المستخدم ──────────────────────────────────────────
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assemblies = relationship("AssemblyRecord", back_populates="worker", foreign_keys="AssemblyRecord.worker_id")
    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])

class BikeType(Base):
    __tablename__ = "bike_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assemblies = relationship("AssemblyRecord", back_populates="bike_type")
    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class BikeColor(Base):
    __tablename__ = "bike_colors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    assemblies = relationship("AssemblyRecord", back_populates="bike_color")
    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class AssemblyRecord(Base):
    __tablename__ = "assembly_records"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    stage = Column(SQLEnum(AssemblyStage), nullable=False)
    bike_type_id = Column(Integer, ForeignKey("bike_types.id"), nullable=True)
    bike_color_id = Column(Integer, ForeignKey("bike_colors.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # ── من قام بتسجيل/تعديل هذا السجل عبر النظام (المسيّر/المشرف) ─────
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    worker = relationship("Worker", back_populates="assemblies", foreign_keys=[worker_id])
    bike_type = relationship("BikeType", back_populates="assemblies")
    bike_color = relationship("BikeColor", back_populates="assemblies")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    status = Column(String, default="active", nullable=False)  # active | cancelled
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)

    # ── تتبع المستخدم ──────────────────────────────────────────
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer = relationship("Customer")
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

class Fault(Base):
    __tablename__ = "faults"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    description = Column(String, nullable=False)
    related_stage = Column(SQLEnum(AssemblyStage), nullable=True)
    reported_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")  # pending, fixed, cancelled
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)

    # ── تتبع المستخدم ──────────────────────────────────────────
    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    repairs = relationship("FaultRepair", back_populates="fault", order_by="FaultRepair.repair_date")
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])


class FaultRepair(Base):
    __tablename__ = "fault_repairs"

    id = Column(Integer, primary_key=True, index=True)
    fault_id = Column(Integer, ForeignKey("faults.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    repair_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    # ── المستخدم الذي سجّل عملية التصليح في النظام (قد يختلف عن العامل الفعلي) ─
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    fault = relationship("Fault", back_populates="repairs")
    worker = relationship("Worker")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


class UserRole(str, enum.Enum):
    ADMIN   = "admin"     # صلاحيات كاملة
    SUPERVISOR = "supervisor"      # إدارة تشغيلية (مبيعات/عملاء/تقارير)
    OPERATOR  = "operator"       # تسجيل تجميع/تصليح فقط
    # أي دور جديد يُضاف هنا مستقبلاً بدون كسر البيانات القديمة


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)