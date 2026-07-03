from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assemblies = relationship("AssemblyRecord", back_populates="worker")

class AssemblyRecord(Base):
    __tablename__ = "assembly_records"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    stage = Column(SQLEnum(AssemblyStage), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    worker = relationship("Worker", back_populates="assemblies")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    sale_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String, nullable=True)

    customer = relationship("Customer")

class Fault(Base):
    __tablename__ = "faults"

    id = Column(Integer, primary_key=True, index=True)
    chassis_number = Column(String, index=True, nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    description = Column(String, nullable=False)
    reported_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")  # pending, fixed