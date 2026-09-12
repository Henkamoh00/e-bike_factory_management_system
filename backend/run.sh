#!/bin/bash

# الانتقال للمسار باستخدام صيغة Linux/Git Bash
cd "/c/Users/Henka/Desktop/projects/electric_bike_manager/backend" || exit

echo "Starting FastAPI Server with Poetry..."

# تشغيل uvicorn من خلال بيئة Poetry
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app

# هذه النقطة تمنع إغلاق النافذة تلقائياً في حال حدوث أي خطأ
echo "Press Enter to exit..."
read