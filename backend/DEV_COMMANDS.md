# أوامر التشغيل الشائعة (Dev Commands Cheat Sheet)

> 📌 هذا هو المصدر **الوحيد** لكل أوامر التشغيل والتطوير المتكررة.
> لا تُنشئ ملفات نصية متفرقة لتذكّر أمر واحد (مثل "طريقة تشغيل الاختبارات.txt") —
> أضف قسمًا هنا بدلاً من ذلك.
>
> كل الأوامر أدناه تُنفَّذ من داخل مجلد `backend/` ما لم يُذكر غير ذلك.

---

## تثبيت الاعتماديات

```bash
cd backend
poetry install --no-interaction --no-root
```

إضافة حزمة جديدة (تُحدّث `pyproject.toml` و`poetry.lock` تلقائيًا):
```bash
poetry add اسم_الحزمة
```

إضافة حزمة تطوير فقط (dev-only):
```bash
poetry add --group dev اسم_الحزمة
```

---

## تشغيل الاختبارات (pytest)

تشغيل كل الاختبارات مع تفاصيل كاملة:
```bash
poetry run pytest test_suite/ -v --tb=short
```

تشغيل ملف اختبار واحد فقط:
```bash
poetry run pytest test_suite/test_auth.py -v
```

تشغيل اختبار واحد محدد بالاسم:
```bash
poetry run pytest test_suite/test_auth.py::test_login_success -v
```

تشغيل مع إيقاف عند أول فشل:
```bash
poetry run pytest test_suite/ -x
```

---

## فحص جودة الكود (flake8)

فحص كامل المشروع (يقرأ الإعدادات تلقائيًا من `.flake8`):
```bash
poetry run flake8 . --count --show-source --statistics
```

فحص ملف واحد فقط:
```bash
poetry run flake8 app/auth_crud.py
```

---

## تشغيل السيرفر محليًا

```bash
poetry run uvicorn app.main:app --reload
```

يفتح تلقائيًا توثيق Swagger على: `http://127.0.0.1:8000/docs`

---

## قاعدة البيانات (Alembic Migrations)

إنشاء migration جديدة تلقائيًا بناءً على تغييرات `models.py`:
```bash
poetry run alembic revision --autogenerate -m "وصف مختصر للتغيير"
```

تطبيق كل الـ migrations المعلّقة على القاعدة:
```bash
poetry run alembic upgrade head
```

التراجع خطوة واحدة للخلف:
```bash
poetry run alembic downgrade -1
```

---

## سكربت الطوارئ: إعادة تعيين كلمة مرور مستخدم

```bash
poetry run python -m app.reset_password --username اسم_المستخدم
```

مع تمرير كلمة مرور مباشرة (بدون إدخال تفاعلي):
```bash
poetry run python -m app.reset_password --username اسم_المستخدم --password "كلمة_مرور_قوية"
```

⚠️ يتطلب وصولاً مباشرًا لبيئة السيرفر (نفس متطلبات `.env`/`DATABASE_URL`).

---

## Git — دورة عمل يومية موصى بها

```bash
git checkout -b feature/اسم-الميزة   # فرع جديد لكل ميزة/إصلاح
git add .
git commit -m "وصف واضح للتغيير"
git push -u origin feature/اسم-الميزة
# ثم افتح Pull Request من GitHub — الدمج المباشر على main محظور الآن
```

---

## قاعدة الإضافة المستقبلية

عند تذكّر أمر تُعيد كتابته أكثر من مرة، أضفه هنا مباشرة تحت القسم المناسب
(أو أنشئ قسمًا جديدًا إن لم يكن هناك قسم مناسب) — بدل حفظه في مكان آخر
تنساه لاحقًا.