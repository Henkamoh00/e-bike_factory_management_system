from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import sqlalchemy as sa
import enum
import secrets
import hashlib
from .database import Base
from sqlalchemy.dialects import postgresql

# يستخدم JSONB مع PostgreSQL، و JSON العادي مع بقية قواعد البيانات (مثل SQLite)
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


class AssemblyStage(str, enum.Enum):
    CHASSIS_ASSEMBLY = "تجميع_الهيكل"
    ELECTRICAL_COVER = "توصيل_الكهرباء_والغلاف"
    FINAL_ASSEMBLY = "تجميع_كامل"


# ── أسماء الأدوار الأساسية (ثوابت بايثون فقط، وليست Enum قاعدة بيانات) ──
# تُستخدم في الراوترز بدلاً من models.UserRole.ADMIN القديمة
class RoleNames:
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    OPERATOR = "operator"


class Role(Base):
    """
    جدول الأدوار المستقل.
    allowed_tabs: قائمة معرّفات التبويبات المسموحة لهذا الدور في لوحة الإدارة
                  (مثال: ["assembly", "faults"])
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    label = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    # 🛡️ server_default صريح يطابق القيمة الفعلية المطبّقة على القاعدة حاليًا:
    # يضمن أن أي إدخال SQL خام (خارج SQLAlchemy) بدون تحديد allowed_tabs
    # يأخذ [] تلقائيًا بدل فشل NOT NULL violation
    allowed_tabs = Column(JSON_TYPE, nullable=False, default=list, server_default=sa.text("'[]'")) # النص العادي يفهمه PostgreSQL و SQLite معاً
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="role_obj")


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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

    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    worker = relationship("Worker", back_populates="assemblies", foreign_keys=[worker_id])
    bike_type = relationship("BikeType", back_populates="assemblies")
    bike_color = relationship("BikeColor", back_populates="assemblies")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    # 🛡️ قيد فريد على مستوى قاعدة البيانات: يمنع نهائيًا وجود أكثر من سجل
    # واحد لنفس (رقم الهيكل + المرحلة) — هذا هو خط الدفاع الأخير ضد
    # Race Condition عند وصول طلبين متزامنين لنفس المرحلة في نفس اللحظة
    # (مثال: عاملان يُسجَّلان لنفس الهيكل بنفس المرحلة في نفس الثانية).
    # منطق Python في create_assembly_record يمنع هذا في الحالة العادية،
    # لكن هذا القيد يضمن الصحة حتى تحت تزامن حقيقي على مستوى الـ DB،
    # بغض النظر عن أي سباق زمني بين قراءة SELECT وتنفيذ commit.
    __table_args__ = (
        UniqueConstraint('chassis_number', 'stage', name='uq_assembly_chassis_stage'),
    )

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    # 🛡️ unique=True لضمان استحالة وجود عميلين نشطين بنفس الاسم على مستوى قاعدة البيانات
    # (بنفس نمط Worker/BikeType/BikeColor) — يمنع تضارب "الاستعادة من الأرشيف" جذريًا
    name = Column(String, unique=True, index=True, nullable=False)
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

    status = Column(String, default="active", nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)

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
    status = Column(String, default="pending")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)

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

    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    fault = relationship("Fault", back_populates="repairs")
    worker = relationship("Worker")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # ── الدور أصبح Foreign Key على جدول roles بدلاً من Enum ──────────
    # ملاحظة: اسم العلاقة "role_obj" (وليس "role") لتفادي التعارض مع
    # الحقل النصي role الذي نُلحقه ديناميكيًا في auth_crud.py قبل الإرجاع
    # عبر Pydantic (نفس أسلوب customer_name في crud.py)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role_obj = relationship("Role", back_populates="users")

    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # 👇لمعرفة من قام بحذف/تعطيل هذا المستخدم (للأرشيف)
    # 🛡️ index=True: يطابق الفهرس الفعلي الموجود على القاعدة حاليًا
    # (مفيد لأي استعلام مستقبلي يبحث "من قام بأرشفة من")
    deleted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    deleted_by = relationship("User", remote_side=[id], foreign_keys=[deleted_by_id])


class AuditLog(Base):
    """
    سجل تتبع شامل لكل عملية مهمة في النظام (من فعل ماذا ومتى)
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False, index=True)        # create / update / delete / cancel / restore / repair / login
    entity_type = Column(String, nullable=False, index=True)  # worker / customer / sale / fault / assembly / user / role ...
    entity_id = Column(Integer, nullable=True)
    entity_label = Column(String, nullable=True)    # وصف مقروء (مثال: رقم الهيكل أو اسم العميل)
    details = Column(String, nullable=True)         # تفاصيل إضافية اختيارية (نص حر)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")


class RefreshToken(Base):
    """
    🛡️ توكنات التحديث (Refresh Tokens) — تُخزَّن مُجزّأة (hashed) فقط في قاعدة البيانات
    أبدًا لا نخزّن التوكن الخام؛ فقط SHA-256 hash منه، بنفس فلسفة كلمات المرور.
    كل توكن مرتبط بمستخدم، وله تاريخ انتهاء، ويمكن إبطاله (revoke) عند تسجيل الخروج
    أو عند الاشتباه بتسريبه.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    # 🛡️ لتتبع الجهاز/المتصفح (مفيد لعرض "الجلسات النشطة" مستقبلاً ولاكتشاف السرقة)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_raw_token() -> str:
        # 🛡️ 32 بايت عشوائية آمنة تشفيريًا (secrets.token_urlsafe)
        return secrets.token_urlsafe(48)
