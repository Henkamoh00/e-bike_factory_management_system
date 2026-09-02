from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

# 🛡️🆕 إعدادات pool صريحة لتفادي أخطاء "server closed the connection unexpectedly"
# الصامتة بعد فترة خمول طويلة (شائعة مع مزوّدي استضافة القواعد السحابية
# مثل Render/Railway/Supabase التي تُغلق الاتصالات الخاملة من جهتها بعد مهلة معينة):
#
# - pool_pre_ping=True: يُنفّذ SELECT 1 خفيف قبل استخدام أي اتصال من الـ pool
#   للتأكد أنه لا يزال حيًا؛ لو كان الاتصال ميتًا يُستبدل تلقائيًا وبشفافية
#   بدل أن يفشل الطلب الفعلي بخطأ غامض للمستخدم.
# - pool_recycle=1800: يُعيد تدوير أي اتصال عمره أكبر من 30 دقيقة استباقيًا،
#   حتى لا يعتمد النظام فقط على pre_ping (بعض المزوّدين يُغلقون الاتصال بصمت
#   دون أن يفشل ping فورًا في كل الحالات).
# - pool_size / max_overflow: سقف معقول لعدد الاتصالات المتزامنة مع القاعدة
#   لتفادي استنزاف حد الاتصالات المسموح به من مزوّد الاستضافة.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()