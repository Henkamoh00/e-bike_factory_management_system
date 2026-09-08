from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys, os
from dotenv import load_dotenv


# 🛡️ يضمن استيراد حزمة الباك إند بغض النظر عن مجلد التشغيل الحالي
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# تحميل متغيرات البيئة من .env (نفس ملف database.py بالضبط)
load_dotenv()


from app.database import Base
from app.database import DATABASE_URL
import app.models
import invoicing.models


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# كائن Alembic Config، يوفر الوصول لقيم ملف alembic.ini
config = context.config

# 🛡️ حقن DATABASE_URL من .env مباشرة بدل الاعتماد على alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# إعداد التسجيل (logging) وفق ملف .ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# metadata الهدف: يُستخدم من طرف 'autogenerate' لمقارنة النماذج بقاعدة البيانات فعليًا
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 🛡️ يجعل autogenerate يلتقط تغييرات نوع العمود (مثال: String → Text)
            compare_type=True,
            # 🛡️ يلتقط تغييرات server_default أيضًا
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
