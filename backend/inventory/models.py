from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Part(Base):
    """
    قطعة غيار/مادة مخزون (صواميل، كابلات، بطاريات...). لا يوجد معرّف فريد
    لكل وحدة فردية من القطعة — التتبع يتم على مستوى الكمية الإجمالية فقط
    (current_stock)، وكل حركة (وارد/صادر) مُسجَّلة بشكل دائم في StockMovement
    (نفس فلسفة عدم الحذف الفعلي المعتمدة في كامل النظام).
    """
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    unit = Column(String, nullable=False)  # وحدة القياس: قطعة / متر / كغ ...

    # 🆕 الرصيد الحالي محسوب ومُخزَّن مباشرة (مثل Customer.credit_balance)،
    # يُحدَّث تلقائيًا مع كل حركة عبر inventory_crud.record_movement
    current_stock = Column(Numeric(12, 3), nullable=False, default=0)

    # 🆕 بدل حد أدنى تلقائي للتنبيه (غير منطقي هنا لعدم انتظام الاستهلاك):
    # علم يدوي بسيط يُفعَّله الموظف عند ملاحظة نفاد القطعة، ليظهر ضمن
    # "قائمة الطلبات" المجمَّعة، ويُلغى تلقائيًا يدويًا بعد الطلب
    flagged_for_reorder = Column(Boolean, default=False, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class Supplier(Base):
    """
    🆕 مورّد بسيط (اسم فقط). يُنشأ إما صراحة عبر /api/inventory/suppliers/
    أو ضمنيًا (get-or-create) عند كتابة اسم مورّد جديد أثناء تسجيل حركة
    وارد — نفس نمط get_or_create_worker تمامًا.
    """
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class StockMovement(Base):
    """
    سجل حركة واحدة على المخزون: وارد (in) أو صادر (out). لا يُعدَّل ولا
    يُحذف أبدًا (أثر دائم). balance_after يحفظ رصيد القطعة فور هذه الحركة
    تحديدًا، لإمكانية إعادة بناء تاريخ المخزون الكامل من هذا الجدول وحده
    (نفس نمط CustomerCreditAction.balance_after تمامًا).
    """
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False, index=True)

    movement_type = Column(String, nullable=False)  # "in" | "out"
    quantity = Column(Numeric(12, 3), nullable=False)
    balance_after = Column(Numeric(12, 3), nullable=False)

    # 🆕 السعر لحظة الوارد فقط (يبقى None دائمًا في حركات الصادر)
    unit_price = Column(Numeric(12, 2), nullable=True)

    # 🆕 المورّد الآن علاقة حقيقية بجدول suppliers بدل نص حر — يُملأ فقط
    # في حركات الوارد (get-or-create عبر inventory_crud.record_movement)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # 🆕 ربط توثيقي اختياري فقط بدراجة معيّنة (نص حر، بلا قيد FK)، لا يُستخدم
    # في أي حساب آلي — تمامًا مثل تخزين chassis_number كنص عادي في بقية النظام
    related_chassis_number = Column(String, nullable=True, index=True)

    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    part = relationship("Part")
    supplier = relationship("Supplier")
    created_by = relationship("User", foreign_keys=[created_by_id])
