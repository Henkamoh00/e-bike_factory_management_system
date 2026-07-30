from backend.app.database import engine, SessionLocal
from backend.app.models import Base, User, UserRole  # استيراد UserRole للـ Enum
from backend.app.security import hash_password

# 1. حذف وإنشاء الجداول
Base.metadata.drop_all(bind=engine)
print('تم حذف الجداول')    
Base.metadata.create_all(bind=engine)
print('تم إنشاء الجداول الجديدة بنجاح')

# 2. إنشاء حساب الأدمن الافتراضي تلقائياً
db = SessionLocal()
try:
    # التأكد من التشفير وقيمة الـ Enum المناسبة
    admin = User(
        username="admin",
        full_name="المدير الرئيسي",
        hashed_password=hash_password("123456"),
        role=UserRole.ADMIN,
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