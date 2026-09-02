1. [TRUSTED_PROXY_IPS] في (.env): اضبط عنوان IP الخاص بـ Nginx/Cloudflare لتفادي حظر جميع المستخدمين جماعياً في Rate Limiting.
2. [JWT_SECRET_KEY] في (.env): استبدل القيمة الافتراضية بـ Key عشوائي آمن عبر (openssl rand -hex 32) لتأمين جلسات المستخدمين.
3. [COOKIE_SECURE] في (.env): اضبط القيمة إلى 'true' عند تشغيل HTTPS لتشفير التوكينات في المتصفح.
4. [DATABASE_URL] في (.env): استبدل بيانات SQLite ببيانات PostgreSQL المعتمدة في الإنتاج وإلغاء صلاحيات Superuser.
5. [REDIS_URL] في (.env): تأكد من إدخال رابط Redis حقيقي مع التشفير (rediss://) لتسريع الجلسات والـ Rate Limiting.
6. [ENVIRONMENT / DEBUG] في (.env / main.py): تأكد من إيقاف وضع التتبع (DEBUG=False) لعدم تسريب تفاصيل الأخطاء الحساسة (Stack Traces).
7. [CORS_ORIGINS] في (main.py): استبدل النجمة "*" بالنطاقات (Domains) المصرح لها فقط بالوصول للـ API.
8. [ALEMBIC MIGRATIONS] في (Terminal): قم بتشغيل (alembic upgrade head) بدلاً من الاعتماد على (Base.metadata.create_all).