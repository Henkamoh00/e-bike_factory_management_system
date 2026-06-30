from backend.app.database import engine
from backend.app.models import Base
Base.metadata.drop_all(bind=engine)
print('تم حذف الجداول')    
Base.metadata.create_all(bind=engine)
print('تم إنشاء الجداول الجديدة بنجاح')
