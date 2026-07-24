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

    assemblies = relationship("AssemblyRecord", back_populates="worker")

class BikeType(Base):
    __tablename__ = "bike_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assemblies = relationship("AssemblyRecord", back_populates="bike_type")


class BikeColor(Base):
    __tablename__ = "bike_colors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assemblies = relationship("AssemblyRecord", back_populates="bike_color")


class AssemblyRecord(Base):
    __tablename__ = "assembly_records"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    stage = Column(SQLEnum(AssemblyStage), nullable=False)
    bike_type_id = Column(Integer, ForeignKey("bike_types.id"), nullable=True)
    bike_color_id = Column(Integer, ForeignKey("bike_colors.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    worker = relationship("Worker", back_populates="assemblies")
    bike_type = relationship("BikeType", back_populates="assemblies")
    bike_color = relationship("BikeColor", back_populates="assemblies")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    # ملاحظة: لم يعد unique، لأن هيكل واحد ممكن يكون له أكثر من سجل بيع
    # (بيع ملغى + بيع نشط لاحق). القيد الفعلي (بيع نشط واحد فقط لكل هيكل)
    # يُفرض على مستوى الكود في crud.create_sale
    chassis_number = Column(String, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    status = Column(String, default="active", nullable=False)  # active | cancelled
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)

    customer = relationship("Customer")

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

    repairs = relationship("FaultRepair", back_populates="fault", order_by="FaultRepair.repair_date")


class FaultRepair(Base):
    __tablename__ = "fault_repairs"

    id = Column(Integer, primary_key=True, index=True)
    fault_id = Column(Integer, ForeignKey("faults.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    repair_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    fault = relationship("Fault", back_populates="repairs")
    worker = relationship("Worker")