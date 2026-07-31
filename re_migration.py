from backend.app.database import engine, SessionLocal
from backend.app.models import Base, User, Role  # استيراد نموذج Role بدلاً من Enum
from backend.app.security import hash_password
from sqlalchemy import text

# 1. حذف وإنشاء الجداول
Base.metadata.drop_all(bind=engine)
print('تم حذف الجداول')    
Base.metadata.create_all(bind=engine)
print('تم إنشاء الجداول الجديدة بنجاح')

# 2. إضافة الأدوار الأساسية (Roles Seed)
roles_seed = [
    ("admin", "مدير النظام", "صلاحيات كاملة للتحكم في كافة أجزاء النظام", True),
    ("supervisor", "مشرف", "إدارة العمليات اليومية وتعديل البيانات الأساسية", True),
    ("user", "مستخدم", "صلاحيات العرض وإدخال العمليات المحددة", True)
]

with engine.begin() as conn:
    for name, label, desc, is_system in roles_seed:
        conn.execute(
            text("""
                INSERT INTO roles (name, label, description, is_system)
                VALUES (:name, :label, :description, :is_system)
                ON CONFLICT (name) DO NOTHING
            """),
            {"name": name, "label": label, "description": desc, "is_system": is_system}
        )
print('✅ تم إدخال الأدوار الأساسية بنجاح')

# 3. إنشاء حساب الأدمن الافتراضي
db = SessionLocal()
try:
    # جلب كائن دور الأدمن من قاعدة البيانات
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    
    admin = User(
        username="admin",
        full_name="المدير الرئيسي",
        hashed_password=hash_password("123456"),
        role_id=admin_role.id,  # استخدام role_id بدلاً من role
        is_active=True
    )
    db.add(admin)
    db.commit()
    print('✅ تم إضافة المستخدم الأدمن الافتراضي (admin / 123456) بنجاح!')
except Exception as e:
    db.rollback()
    print(f'❌ حدث خطأ أثناء إضافة الأدمن: {e}')
finally:
    db.close()