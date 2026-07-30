from backend.app.database import SessionLocal
from backend.app.models import User, UserRole  # أو حسب مسمى الـ Enum لديك
from backend.app.security import get_password_hash

def create_initial_admin():
    db = SessionLocal()
    try:
        admin_user = User(
            username="admin",
            full_name="المدير الرئيسي",
            hashed_password=get_password_hash("123456"),
            role=UserRole.ADMIN, # سيقوم Python بإنشائها بالصيغة الصحيحة للـ Enum
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("✅ تم إنشاء حساب الأدمن الافتراضي بنجاح!")
    except Exception as e:
        db.rollback()
        print(f"❌ حدث خطأ: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()