"""
🆘 سكربت طوارئ لإعادة تعيين كلمة مرور أي مستخدم (خاصة الأدمن) مباشرة من السيرفر.

الاستخدام:
    python -m app.reset_password --username ahmed_admin
    python -m app.reset_password --username ahmed_admin --password "NewStrongPass123!"

- إذا لم تُمرَّر --password، سيُطلب إدخالها تفاعليًا (مخفية، بدون طباعة على الشاشة).
- يتطلب وصولاً مباشرًا لبيئة السيرفر (نفس متطلبات .env / DATABASE_URL).
- يُبطل تلقائيًا كل جلسات المستخدم الحالية (refresh tokens) بعد التغيير،
  بنفس المنطق الأمني المتبع في auth_crud.update_user عند تغيير كلمة المرور.
- يسجّل العملية في audit_logs بوضوح كإجراء طوارئ، حتى يبقى الأثر موثقًا.

⚠️ هذا السكربت لا يمر عبر أي API أو صلاحيات تطبيقية — فقط لمن يملك وصولاً
فعليًا لبيئة السيرفر/القاعدة أصلاً (وهو نفس المستوى المطلوب للتعديل اليدوي
المباشر في قاعدة البيانات، لكن بأمان أكبر وبأثر موثّق).
"""

import argparse
import getpass
import sys

from .database import SessionLocal
from . import models, audit_crud
from .security import hash_password
from .auth_crud import revoke_all_user_tokens


MIN_PASSWORD_LENGTH = 8


def _prompt_password() -> str:
    while True:
        pwd1 = getpass.getpass("كلمة المرور الجديدة: ")
        if len(pwd1) < MIN_PASSWORD_LENGTH:
            print(f"❌ كلمة المرور يجب أن تكون {MIN_PASSWORD_LENGTH} أحرف على الأقل على الأقل. حاول مجدداً.\n")
            continue
        pwd2 = getpass.getpass("تأكيد كلمة المرور: ")
        if pwd1 != pwd2:
            print("❌ كلمتا المرور غير متطابقتين. حاول مجدداً.\n")
            continue
        return pwd1


def reset_password(username: str, new_password: str | None = None) -> int:
    db = SessionLocal()
    try:
        user = (
            db.query(models.User)
            .filter(models.User.username == username, models.User.is_deleted.is_(False))
            .first()
        )

        if not user:
            print(f"❌ لا يوجد مستخدم نشط باسم '{username}'.")

            # نساعد المشغّل بعرض المستخدمين المؤرشفين بنفس الاسم إن وُجدوا،
            # لتفادي الالتباس (مثال: أدمن مؤرشف بالخطأ ويحتاج استعادة أولاً وليس فقط تغيير كلمة مرور)
            archived = (
                db.query(models.User)
                .filter(models.User.username == username, models.User.is_deleted.is_(True))
                .first()
            )
            if archived:
                print(
                    "⚠️ ملاحظة: يوجد مستخدم بنفس الاسم لكنه مؤرشف (is_deleted=True). "
                    "يجب استعادته أولاً (عبر لوحة الإدارة أو تعديل is_deleted يدويًا) قبل إعادة تعيين كلمة مروره."
                )
            return 1

        role_label = user.role_obj.label if user.role_obj else "بدون دور"
        print(f"✅ تم العثور على المستخدم: {user.username} ({role_label}) — نشط: {user.is_active}")

        confirm = input(f"هل أنت متأكد من إعادة تعيين كلمة مرور '{username}'؟ (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("تم الإلغاء.")
            return 1

        if not new_password:
            new_password = _prompt_password()
        elif len(new_password) < MIN_PASSWORD_LENGTH:
            print(f"❌ كلمة المرور يجب أن تكون {MIN_PASSWORD_LENGTH} أحرف على الأقل.")
            return 1

        user.hashed_password = hash_password(new_password)

        # إعادة تفعيل الحساب تلقائيًا إن كان معطلاً — سيناريو شائع في حالات
        # الطوارئ (أدمن معطَّل بالخطأ بلا أدمن آخر لتفعيله عبر الواجهة)
        was_inactive = not user.is_active
        if was_inactive:
            user.is_active = True

        db.commit()
        db.refresh(user)

        # إبطال كل الجلسات الحالية فورًا، بنفس منطق تغيير كلمة المرور
        # العادي عبر الواجهة (auth_crud.update_user) — أي جهاز قديم لن يستطيع
        # تجديد التوكن بعد الآن
        revoke_all_user_tokens(db, user.id)

        details = "🆘 إعادة تعيين طارئة عبر سكربت CLI مباشرة من السيرفر"
        if was_inactive:
            details += " (وتمت إعادة تفعيل الحساب تلقائيًا)"

        audit_crud.log_action(
            db,
            action="update",
            entity_type="user",
            entity_id=user.id,
            user_id=None,  # لا يوجد current_user حقيقي — العملية من خارج التطبيق
            entity_label=user.username,
            details=details,
        )

        print(f"✅ تم تحديث كلمة مرور '{username}' بنجاح، وتم إبطال كل جلساته الحالية.")
        if was_inactive:
            print("✅ كما تمت إعادة تفعيل الحساب تلقائيًا (كان معطلاً).")
        return 0

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="🆘 سكربت طوارئ لإعادة تعيين كلمة مرور مستخدم مباشرة من السيرفر."
    )
    parser.add_argument("--username", required=True, help="اسم المستخدم المطلوب إعادة تعيين كلمة مروره")
    parser.add_argument(
        "--password",
        required=False,
        default=None,
        help="كلمة المرور الجديدة (اختياري — لو لم تُمرَّر سيُطلب إدخالها تفاعليًا وبأمان)",
    )
    args = parser.parse_args()

    exit_code = reset_password(args.username, args.password)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
