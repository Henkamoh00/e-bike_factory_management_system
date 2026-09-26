# 🚲 Electric Bike Assembly Management System

A full-stack workshop management system for tracking the complete lifecycle of electric bikes — from assembly on the shop floor, through sales and invoicing, to fault reporting and repairs. Built around a strict **Audit Trail philosophy**: no hard deletes of historical data, ever. Everything is soft-deleted (archivable/restorable), and every action is logged with who did what and when.

> Originally built for an Algerian e-bike workshop; the domain logic (Arabic labels, Africa/Algiers timezone handling) is intentionally localized, while the architecture is fully generic and reusable.

---

## ✨ Key Features

- **Invoicing system** with partial payments, discounts, cancellations, returns, and a per-customer internal **credit wallet** (auto-refills from cancellations/returns, supports manual deposits, cash refunds, and cross-invoice reallocation)
- **Tamper-proof invoice verification**: every printed invoice carries a QR code linking to a public verification page. The page always reflects the *live* database state — editing a printed PDF changes nothing, because verification is HMAC-signed server-side, not file-based
- **Dynamic role-based access control**: roles and their tab permissions are stored in the database and editable from the UI — not hardcoded enums. `admin` always retains full access as a safety net against accidental lockout
- **Full audit trail**: every create/update/delete/restore/cancel is logged (`audit_logs` table) with actor, timestamp, and human-readable label. Logging failures never break the underlying operation (best-effort logging)
- **Soft-delete everywhere**: workers, customers, bike types/colors, users — nothing is hard-deleted. Everything is archivable and restorable with duplicate-name protection on restore
- **Race-condition-safe assembly recording**: row-level locking (`SELECT ... FOR UPDATE`) plus a database `UNIQUE` constraint as a final safety net, so two concurrent requests can never create conflicting records for the same chassis
- **Refresh token rotation**: every refresh token use invalidates itself and issues a new one; reuse of a revoked token triggers an automatic full session wipe for that user (stolen-token detection)
- **CSRF protection** (Double Submit Cookie pattern) on top of httpOnly JWT cookies
- **Per-user rate limiting** (not per-IP) on sensitive write endpoints, with automatic Redis → in-memory fallback
- **Inventory / spare-parts module** with a simple in/out stock ledger and a manual reorder-flag workflow
- **Unified UTC storage with Africa/Algiers display logic** — a single source of truth (`time_utils.py`) for all datetime handling, with dedicated tests for day-boundary edge cases (payments just before/after local midnight)
- **Comprehensive automated test suite** — two isolated pytest suites (core system + invoicing), each with its own SQLite database, covering permission boundaries, financial edge cases (surplus payments, partial returns, discount floors), and concurrency-sensitive flows

---

## 🛠️ Tech Stack

### Backend
| Tool | Purpose |
|---|---|
| **FastAPI** | Core web framework |
| **SQLAlchemy 2.x** | ORM |
| **Alembic** | Database schema migrations |
| **PostgreSQL** | Primary database (SQLite used only for isolated tests) |
| **Poetry** | Dependency management & virtual environment (see below) |
| **python-jose** | JWT issuing/verification |
| **bcrypt** | Password hashing |
| **slowapi** | Rate limiting, with optional Redis backend |
| **ReportLab + arabic-reshaper + python-bidi** | Arabic-aware PDF generation (RTL shaping) |
| **qrcode** | QR code generation for invoice verification |
| **pytest** | Testing |
| **flake8** | Linting (CI-enforced) |

### Frontend
| Tool | Purpose |
|---|---|
| **Vue 3** (Composition API, `<script setup>`) | UI framework |
| **Vue Router** | Routing with session/permission guards |
| **Vite** | Build tool & dev server |
| **Tailwind CSS** | Styling |

### CI/CD
- **GitHub Actions**: lint (flake8) + both test suites run on every push/PR to `main`/`master`.

---

## 📁 Project Structure
backend/
├── app/ # Core domain: users, roles, workers, assembly, faults, customers
├── invoicing/ # Invoicing module: invoices, payments, returns, customer credit, PDF, QR verification
├── inventory/ # Spare-parts stock module
├── migrations/ # Alembic migration scripts
├── test_suite/ # Core system tests (isolated SQLite DB)
├── test_suite_invoices/ # Invoicing module tests (separate isolated SQLite DB)
├── scripts/ # Maintenance scripts (e.g. EOF newline fixer)
├── pyproject.toml / poetry.lock
├── alembic.ini
├── .flake8
└── .env.example

frontend/
├── src/
│ ├── views/ # Page-level components (Login, Dashboard, Invoices, Inventory)
│ ├── components/
│ │ ├── admin/ # Dashboard tabs & modals
│ │ ├── invoicing/ # Invoicing UI
│ │ ├── inventory/ # Inventory UI
│ │ └── shared/ # Reusable components (pagination, toasts, bulk actions...)
│ ├── composables/ # useAuth, useServerPagination, useBulkSelection...
│ └── router/
├── package.json
└── .env.example


---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (or any SQLAlchemy-compatible engine)
- [Poetry](https://python-poetry.org/) for backend dependency management
- Redis *(optional)* — enables distributed rate limiting; falls back safely to in-memory if unavailable

### Backend Setup

```bash
cd backend
poetry install --no-interaction --no-root
```

Create your `.env` from the template and fill in real values:

```bash
cp .env.example .env
```

> **All required and optional environment variables — with inline explanations of what each one does and how to generate secrets — are documented directly in `.env.example`.** Read it before running the server; the app will refuse to start without a few of them (`JWT_SECRET_KEY`, `INVOICE_VERIFICATION_SECRET_KEY`, `INVOICE_VERIFY_BASE_URL`) as a deliberate safeguard against running with insecure defaults.

Apply database migrations:

```bash
poetry run alembic upgrade head
```

Create the initial admin account and system roles:

```bash
poetry run python -m app.seed --username admin
```

Run the server:

```bash
poetry run uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Interactive docs (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App runs at `http://localhost:5173` by default.

---

## 🧪 Testing

Two independent, fully isolated test suites (separate SQLite databases, auto-created/destroyed per run):

```bash
cd backend
poetry run pytest test_suite/ -v --tb=short
poetry run pytest test_suite_invoices/ -v --tb=short
```

Both suites run automatically in CI on every push and pull request. Coverage includes:
- Auth flows (login, refresh rotation, stolen-token detection, logout)
- Role/permission boundaries (including cross-tab access edge cases)
- Assembly stage validation and worker-conflict handling
- Full invoicing lifecycle: creation, partial/overpayment, discounts, item edits, cancellations, returns, and their financial ripple effects on customer credit
- Time-boundary correctness (Africa/Algiers local-day cutoffs for daily revenue stats)

### Linting

```bash
poetry run flake8 . --count --show-source --statistics
```

---

## 📐 Coding Standards & Conventions

These are enforced conventions maintained throughout the codebase — useful context if you're reading the source:

- **Time handling**: always go through `app/time_utils.py` (`utcnow()`, `ensure_utc()`, `to_local()`, `format_local()`). Storage is always UTC; display and period boundaries ("today", "this week") use `Africa/Algiers` (fixed UTC+1, no DST). Raw `datetime.utcnow()` and direct aware/naive comparisons are banned project-wide.
- **Linting**: `max-complexity = 10` — functions exceeding this are split into helpers. SQLAlchemy boolean columns are compared with `.is_(False)` / `.is_(True)`, never Python truthiness.
- **Monetary values**: every API response returning amounts uses a Pydantic `Decimal` field (serialized as a two-decimal string, e.g. `"400.00"`) — never a raw `dict` with a `Decimal` (which silently becomes a lossy `float`), and never `x or 0` on a monetary value (since `Decimal("0.00")` is falsy but valid).
- **Soft delete only**: no entity is ever hard-deleted from the database except in narrowly-scoped, explicitly-justified cleanup paths (e.g. deleting a just-created invoice with zero payments and one item, to correct a data-entry mistake).
- **Modular domain packages**: `invoicing/` and `inventory/` follow the same internal layout as `app/` (`models.py` / `schemas.py` / `*_crud.py` / `routers/`) for consistency.

---

## 🔐 Security Notes

- Access tokens (15 min) and refresh tokens (7 days) are stored exclusively in **httpOnly cookies** — never exposed to JavaScript.
- Refresh tokens are stored **hashed** in the database and rotate on every use; reuse of an already-rotated (stolen) token triggers immediate revocation of *all* sessions for that user.
- CSRF protection follows the **Double Submit Cookie** pattern: a non-httpOnly CSRF cookie must match an `X-CSRF-Token` header on every unsafe request from a cookie-bearing client.
- `admin` role permissions can never be restricted through the UI, even by an admin — a deliberate guardrail against accidentally locking everyone out of the system.
- Invoice verification signatures use a secret key that is fully independent from the JWT signing key — a leak of one never compromises the other.

---

## 📌 Deployment Checklist

All of the following are documented with inline comments directly inside `backend/.env.example` — check it for the exact variable names and generation commands:

- Set `TRUSTED_PROXY_IPS` if running behind a reverse proxy/load balancer, otherwise rate limiting falls back to the direct connection IP for everyone.
- Generate strong, unique secrets for `JWT_SECRET_KEY` and `INVOICE_VERIFICATION_SECRET_KEY` (they must remain independent of each other).
- Set `COOKIE_SECURE=true` once serving over HTTPS.
- Point `DATABASE_URL` at your production PostgreSQL instance.
- Set `CORS_ORIGINS` to your real frontend domain(s), comma-separated — never leave it wildcarded.
- Point `INVOICE_VERIFY_BASE_URL` at your actual public API domain (not `localhost`), or QR codes printed on invoices will be unreachable from outside your network.
- Run `alembic upgrade head` on deploy — this project does not rely on `create_all()`.

---

## 📄 License

This project is available under the [MIT License](LICENSE).

---

<br>

# 🚲 نظام إدارة تجميع الدراجات الكهربائية

نظام إداري متكامل (Full-Stack) لتتبع دورة حياة الدراجة الكهربائية بالكامل: من التجميع في الورشة، مرورًا بالبيع والفوترة، وصولاً إلى تسجيل الأعطال وإصلاحها. مبني على فلسفة صارمة لـ**تتبع الأثر الكامل (Audit Trail)**: لا يوجد حذف فعلي للبيانات التاريخية إطلاقًا. كل شيء يُؤرشف بشكل ناعم (قابل للاستعادة)، وكل إجراء يُسجَّل مع تحديد من قام به ومتى.

> صُمم أصلاً لورشة دراجات كهربائية جزائرية؛ منطق المجال (التسميات العربية، التعامل مع توقيت الجزائر) مُخصَّص عمدًا، بينما البنية المعمارية عامة وقابلة لإعادة الاستخدام بالكامل.

---

## ✨ أبرز الميزات

- **نظام فوترة** يدعم الدفعات الجزئية، الخصومات، الإلغاء، الإرجاع، مع **محفظة رصيد داخلية لكل عميل** (تتغذى تلقائيًا من فوائض الإلغاء/الإرجاع، وتدعم الإيداع اليدوي، الاسترجاع النقدي، والتحويل بين الفواتير)
- **تحقق من صحة الفواتير مضاد للتزوير**: كل فاتورة مطبوعة تحمل رمز QR يقود لصفحة تحقق عامة تعكس دائمًا الحالة **الحيّة** لقاعدة البيانات. تعديل نسخة PDF مطبوعة يدويًا لا يُغيّر شيئًا، لأن التحقق موقّع بـ HMAC من جهة السيرفر وليس معتمدًا على الملف نفسه
- **صلاحيات ديناميكية قائمة على الأدوار**: الأدوار وصلاحياتها مخزَّنة في قاعدة البيانات وقابلة للتعديل من الواجهة — وليست Enum ثابتة بالكود. دور `admin` يحتفظ دائمًا بوصول كامل كحماية من قفل النظام بالخطأ
- **سجل أثر كامل**: كل عملية إنشاء/تعديل/حذف/استعادة/إلغاء تُسجَّل في جدول `audit_logs` مع الفاعل والتوقيت ووصف مقروء. فشل التسجيل لا يُفشل العملية الأصلية أبدًا (Best-effort logging)
- **حذف ناعم في كل مكان**: العمال، العملاء، أنواع/ألوان الدراجات، المستخدمون — لا شيء يُحذف فعليًا. كل شيء قابل للأرشفة والاستعادة مع حماية من تعارض الأسماء عند الاستعادة
- **تسجيل تجميع آمن ضد التزامن (Race Conditions)**: قفل على مستوى الصفوف (`SELECT ... FOR UPDATE`) بالإضافة إلى قيد `UNIQUE` في قاعدة البيانات كخط دفاع أخير، بحيث لا يمكن لطلبين متزامنين إنشاء سجلات متضاربة لنفس الهيكل أبدًا
- **تدوير رموز التحديث (Refresh Token Rotation)**: كل استخدام لرمز التحديث يُبطله فورًا ويُصدر رمزًا جديدًا؛ إعادة استخدام رمز مُبطَل (مسروق) تُفعّل إبطالاً شاملاً فوريًا لكل جلسات ذلك المستخدم
- **حماية CSRF** (نمط Double Submit Cookie) فوق كوكيز JWT من نوع httpOnly
- **تحديد معدل الطلبات لكل مستخدم** (وليس لكل IP) على المسارات الحساسة، مع تراجع تلقائي وآمن من Redis إلى الذاكرة المحلية
- **وحدة إدارة مخزون/قطع غيار** بنظام دفتر حركات دخول/خروج بسيط وآلية علم يدوي لإعادة الطلب
- **تخزين موحّد بتوقيت UTC مع منطق عرض بتوقيت الجزائر** — مصدر واحد للحقيقة (`time_utils.py`) لكل التعامل مع الوقت، مع اختبارات مخصصة لحالات حدود اليوم (دفعات قبل/بعد منتصف الليل المحلي مباشرة)
- **مجموعة اختبارات آلية شاملة** — مجموعتا pytest معزولتان تمامًا (النظام الأساسي + الفوترة)، لكل منهما قاعدة SQLite خاصة، تغطي حدود الصلاحيات، الحالات المالية الحدّية (فوائض الدفع، الإرجاع الجزئي، حدود الخصم)، والتدفقات الحساسة للتزامن

---

## 🛠️ التقنيات المستخدمة

### الباك إند
| الأداة | الغرض |
|---|---|
| **FastAPI** | إطار العمل الأساسي |
| **SQLAlchemy 2.x** | ORM |
| **Alembic** | إدارة تحديثات مخطط قاعدة البيانات |
| **PostgreSQL** | قاعدة البيانات الأساسية (SQLite تُستخدم فقط في الاختبارات المعزولة) |
| **Poetry** | إدارة الاعتماديات والبيئة الافتراضية (راجع القسم أدناه) |
| **python-jose** | إصدار والتحقق من JWT |
| **bcrypt** | تشفير كلمات المرور |
| **slowapi** | تحديد معدل الطلبات، مع دعم Redis اختياري |
| **ReportLab + arabic-reshaper + python-bidi** | توليد PDF يدعم العربية (تشكيل واتجاه RTL) |
| **qrcode** | توليد رموز QR للتحقق من الفواتير |
| **pytest** | الاختبارات |
| **flake8** | فحص جودة الكود (مُفعَّل في CI) |

### الفرونت إند
| الأداة | الغرض |
|---|---|
| **Vue 3** (Composition API، `<script setup>`) | إطار عمل الواجهة |
| **Vue Router** | التوجيه مع حراسة الجلسة والصلاحيات |
| **Vite** | أداة البناء وخادم التطوير |
| **Tailwind CSS** | التنسيق |

### CI/CD
- **GitHub Actions**: فحص الكود (flake8) وتشغيل كلتا مجموعتي الاختبارات تلقائيًا مع كل push أو pull request على `main`/`master`.

---

## 📁 بنية المشروع
backend/
├── app/ # النواة: المستخدمون، الأدوار، العمال، التجميع، الأعطال، العملاء
├── invoicing/ # وحدة الفوترة: الفواتير، الدفعات، الإرجاع، رصيد العميل، PDF، تحقق QR
├── inventory/ # وحدة إدارة المخزون
├── migrations/ # سكربتات Alembic لتحديث قاعدة البيانات
├── test_suite/ # اختبارات النظام الأساسي (قاعدة SQLite معزولة)
├── test_suite_invoices/ # اختبارات وحدة الفوترة (قاعدة SQLite معزولة منفصلة)
├── scripts/ # سكربتات صيانة (مثل تصحيح نهاية الأسطر)
├── pyproject.toml / poetry.lock
├── alembic.ini
├── .flake8
└── .env.example

frontend/
├── src/
│ ├── views/ # صفحات كاملة (تسجيل الدخول، اللوحة، الفواتير، المخزون)
│ ├── components/
│ │ ├── admin/ # تبويبات ونوافذ لوحة الإدارة
│ │ ├── invoicing/ # واجهة الفوترة
│ │ ├── inventory/ # واجهة المخزون
│ │ └── shared/ # مكوّنات مشتركة (Pagination، Toasts، إجراءات جماعية...)
│ ├── composables/ # useAuth، useServerPagination، useBulkSelection...
│ └── router/
├── package.json
└── .env.example


---

## 🚀 التشغيل

### المتطلبات
- Python 3.10+
- Node.js 18+
- PostgreSQL (أو أي محرك متوافق مع SQLAlchemy)
- [Poetry](https://python-poetry.org/) لإدارة اعتماديات الباك إند
- Redis *(اختياري)* — يفعّل تحديد المعدل الموزّع؛ يتراجع تلقائيًا وبأمان إلى الذاكرة المحلية إن لم يكن متاحًا

### إعداد الباك إند

```bash
cd backend
poetry install --no-interaction --no-root
```

أنشئ ملف `.env` من القالب واملأ القيم الحقيقية:

```bash
cp .env.example .env
```

> **كل متغيرات البيئة المطلوبة والاختيارية — مع شرح مضمّن لدور كل واحد وكيفية توليد الأسرار — موثّقة مباشرة داخل `.env.example`.** اقرأه قبل تشغيل السيرفر؛ التطبيق يرفض الإقلاع بدون بعضها (`JWT_SECRET_KEY`، `INVOICE_VERIFICATION_SECRET_KEY`، `INVOICE_VERIFY_BASE_URL`) كإجراء وقائي متعمد ضد التشغيل بقيم افتراضية غير آمنة.

طبّق تحديثات قاعدة البيانات:

```bash
poetry run alembic upgrade head
```

أنشئ حساب المدير الأول والأدوار الأساسية:

```bash
poetry run python -m app.seed --username admin
```

شغّل السيرفر:

```bash
poetry run uvicorn app.main:app --reload
```

- الـ API: `http://localhost:8000`
- توثيق Swagger التفاعلي: `http://localhost:8000/docs`
- فحص الصحة: `http://localhost:8000/health`

### إعداد الفرونت إند

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

الواجهة تعمل افتراضيًا على `http://localhost:5173`.

---

## 🧪 الاختبارات

مجموعتا اختبار مستقلتان ومعزولتان تمامًا (قاعدتا SQLite منفصلتان تُنشآن وتُحذفان تلقائيًا مع كل تشغيل):

```bash
cd backend
poetry run pytest test_suite/ -v --tb=short
poetry run pytest test_suite_invoices/ -v --tb=short
```

تُشغَّل المجموعتان تلقائيًا في CI مع كل push و pull request. التغطية تشمل:
- تدفقات المصادقة (تسجيل الدخول، تدوير رمز التحديث، كشف الرموز المسروقة، تسجيل الخروج)
- حدود الأدوار والصلاحيات (بما فيها حالات الوصول العابر للتبويبات)
- التحقق من مراحل التجميع والتعامل مع تعارض العمال
- دورة حياة الفوترة الكاملة: الإنشاء، الدفع الجزئي/الزائد، الخصومات، تعديل البنود، الإلغاء، الإرجاع، وتأثيراتها المالية المتسلسلة على رصيد العميل
- صحة حدود التوقيت (حدود اليوم المحلي بتوقيت الجزائر لإحصائيات الإيرادات اليومية)

### فحص جودة الكود

```bash
poetry run flake8 . --count --show-source --statistics
```

---

## 📐 معايير الكود والاتفاقيات

هذه اتفاقيات مُطبَّقة عبر كامل المشروع — مفيدة كسياق عند قراءة الكود المصدري:

- **التعامل مع الوقت**: دائمًا عبر `app/time_utils.py` (`utcnow()`، `ensure_utc()`، `to_local()`، `format_local()`). التخزين دائمًا بتوقيت UTC، والعرض وحدود الفترات ("اليوم"، "هذا الأسبوع") بتوقيت `Africa/Algiers` (UTC+1 ثابت، بلا توقيت صيفي). استخدام `datetime.utcnow()` مباشرة أو مقارنة وقت aware مع naive ممنوع في كل المشروع.
- **فحص الكود**: `max-complexity = 10` — أي دالة تتجاوز هذا الحد تُقسَّم إلى دوال مساعدة. أعمدة SQLAlchemy المنطقية تُقارَن بـ `.is_(False)` / `.is_(True)`، لا عبر Truthiness في بايثون.
- **المبالغ المالية**: كل استجابة API تُرجع مبالغ تستخدم حقل `Decimal` من Pydantic (يُسلسَل كنص بمنزلتين عشريتين، مثال `"400.00"`) — أبدًا `dict` خام فيه `Decimal` (يتحول بصمت إلى `float` فاقد للدقة)، وأبدًا `x or 0` على قيمة مالية (لأن `Decimal("0.00")` يُقيَّم كـ False رغم كونه قيمة صحيحة).
- **حذف ناعم فقط**: لا يُحذف أي كيان فعليًا من قاعدة البيانات إلا في مسارات تنظيف محدودة النطاق ومبرَّرة صراحة (مثال: حذف فاتورة أُنشئت للتو ببند واحد وبدون أي دفعات، لتصحيح خطأ إدخال).
- **حزم مجال معيارية**: `invoicing/` و`inventory/` تتبعان نفس البنية الداخلية لـ `app/` (`models.py` / `schemas.py` / `*_crud.py` / `routers/`) للحفاظ على الاتساق.

---

## 🔐 ملاحظات أمنية

- رموز الوصول (15 دقيقة) ورموز التحديث (7 أيام) تُخزَّن حصريًا في **كوكيز httpOnly** — لا تصل إلى JavaScript إطلاقًا.
- رموز التحديث تُخزَّن **مُجزَّأة (hashed)** في قاعدة البيانات وتُدوَّر مع كل استخدام؛ إعادة استخدام رمز سبق تدويره (مسروق) تُفعّل إبطالاً فوريًا لكل جلسات ذلك المستخدم.
- حماية CSRF تتبع نمط **Double Submit Cookie**: كوكي CSRF غير httpOnly يجب أن يطابق هيدر `X-CSRF-Token` في كل طلب غير آمن من عميل يحمل جلسة كوكيز.
- صلاحيات دور `admin` لا يمكن تقييدها عبر الواجهة أبدًا، حتى من قِبل مدير آخر — حماية متعمدة من قفل النظام بالكامل بالخطأ.
- توقيعات التحقق من الفواتير تستخدم مفتاحًا سريًا مستقلاً تمامًا عن مفتاح توقيع JWT — تسريب أحدهما لا يُعرِّض الآخر للخطر أبدًا.

---

## 📌 قائمة تحقق قبل النشر

كل ما يلي موثّق بتعليقات مضمّنة مباشرة داخل `backend/.env.example` — راجعه لمعرفة أسماء المتغيرات الدقيقة وأوامر التوليد:

- اضبط `TRUSTED_PROXY_IPS` إن كان السيرفر خلف بروكسي/موزّع أحمال، وإلا سيتراجع تحديد المعدل لاستخدام عنوان IP المباشر لكل المستخدمين معًا.
- ولّد أسرارًا قوية وفريدة لـ `JWT_SECRET_KEY` و`INVOICE_VERIFICATION_SECRET_KEY` (يجب أن يبقيا مستقلَّين عن بعضهما).
- اضبط `COOKIE_SECURE=true` عند التشغيل عبر HTTPS.
- وجّه `DATABASE_URL` إلى قاعدة PostgreSQL الفعلية للإنتاج.
- اضبط `CORS_ORIGINS` على نطاق(ات) الفرونت إند الحقيقية مفصولة بفواصل — لا تتركه مفتوحًا بعلامة `*` أبدًا.
- وجّه `INVOICE_VERIFY_BASE_URL` إلى نطاق API العام الفعلي (وليس `localhost`)، وإلا ستكون رموز QR المطبوعة على الفواتير غير قابلة للوصول من خارج شبكتك.
- شغّل `alembic upgrade head` عند كل نشر — هذا المشروع لا يعتمد على `create_all()`.

---

## 📄 الترخيص

هذا المشروع متاح بموجب [رخصة MIT](LICENSE).