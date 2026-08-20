# 1. تأكد أن القاعدة الحالية تحتوي فعلاً على كل الجداول (لأنك أنشأتها سابقًا عبر create_all)

# 2. أنشئ أول migration تلقائيًا من الوضع الحالي للنماذج
alembic revision --autogenerate -m "المخطط الأولي"

# 3. راجع الملف المُولَّد يدويًا داخل alembic/versions/ قبل التطبيق
#    (autogenerate أحيانًا يفوت بعض القيود اليدوية مثل UNIQUE constraint على customers.name
#     الذي طبقته سابقًا بـ ALTER TABLE يدوي — تأكد من وجوده في upgrade())

# 4. بما أن الجداول موجودة فعلاً في القاعدة (من create_all القديم)، لا تُشغّل upgrade عاديًا
#    (سيحاول إعادة إنشاء جداول موجودة ويفشل). بدلاً من ذلك، "زيّف" التطبيق:
alembic stamp head

# من الآن فصاعدًا، أي تغيير على models.py:
alembic revision --autogenerate -m "وصف التغيير"
alembic upgrade head




poetry run alembic revision --autogenerate -m "المخطط الأولي"
poetry run alembic stamp head  
poetry run alembic current