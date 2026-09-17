1. [TRUSTED_PROXY_IPS] في (.env): اضبط عنوان IP الخاص بـ Nginx/Cloudflare لتفادي حظر جميع المستخدمين جماعياً في Rate Limiting.
2. [JWT_SECRET_KEY] في (.env): استبدل القيمة الافتراضية بـ Key عشوائي آمن عبر (openssl rand -hex 32) لتأمين جلسات المستخدمين.
3. [COOKIE_SECURE] في (.env): اضبط القيمة إلى 'true' عند تشغيل HTTPS لتشفير التوكينات في المتصفح.
4. [DATABASE_URL] في (.env): استبدل بيانات SQLite ببيانات PostgreSQL المعتمدة في الإنتاج وإلغاء صلاحيات Superuser.
5. [REDIS_URL] في (.env): تأكد من إدخال رابط Redis حقيقي مع التشفير (rediss://) لتسريع الجلسات والـ Rate Limiting.
6. [ENVIRONMENT / DEBUG] في (.env / main.py): تأكد من إيقاف وضع التتبع (DEBUG=False) لعدم تسريب تفاصيل الأخطاء الحساسة (Stack Traces).
7. [CORS_ORIGINS] في (main.py): استبدل النجمة "*" بالنطاقات (Domains) المصرح لها فقط بالوصول للـ API.
8. [ALEMBIC MIGRATIONS] في (Terminal): قم بتشغيل (alembic upgrade head) بدلاً من الاعتماد على (Base.metadata.create_all).
9. [رمز QR للتحقق من الفواتير] في (.env) — ثلاثة متغيرات إلزامية لعمل ميزة توليد PDF للفاتورة (السيرفر يرفض الإقلاع بدونها بسبب الفحص الصريح في invoicing/verification.py):
   - [INVOICE_VERIFICATION_SECRET_KEY]: مفتاح سرّي عشوائي مستقل تمامًا عن JWT_SECRET_KEY، يُستخدم فقط لتوقيع HMAC لروابط التحقق من الفواتير. ولّده عبر (python -c "import secrets; print(secrets.token_hex(32))") ولا تُعد استخدامه لأي غرض آخر.
   - [INVOICE_VERIFY_BASE_URL]: رابط السيرفر العام الفعلي الذي سيُطبع داخل رمز QR على الفاتورة (مثال: https://api.yourdomain.com) — يجب أن يكون Domain حقيقي يصل إليه أي زائر من الإنترنت (وليس localhost أو IP داخلي)، وإلا سيفشل مسح رمز QR من أي هاتف خارج الشبكة الداخلية.
   - [INVOICE_VERIFY_PATH_PREFIX] (اختياري): المسار العشوائي المظهر لصفحة التحقق العامة، الافتراضي "/dq7f-doc-chk-2x9k". يمكن تغييره لقيمة عشوائية أخرى من اختيارك، لكن تجنّب أي قيمة توحي بارتباطه بالتطبيق (لا تستخدم كلمات مثل invoice أو verify أو api).
   بعد ضبط هذه المتغيرات، تأكد من أن [INVOICE_VERIFY_BASE_URL] تحديدًا يشير لنفس الدومين الذي يخدم راوتر invoice_verify_router في main.py (لا يمر عبر أي Auth أو CORS نظرًا لكونه صفحة عامة)، وأن أي Reverse Proxy أمامه (Nginx/Cloudflare) لا يحظر هذا المسار تحديدًا عبر أي قاعدة WAF عامة تستهدف المسارات العشوائية المظهر.