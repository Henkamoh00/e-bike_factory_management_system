"""
scripts/fix_eof_newline.py

ينظّف نهاية كل ملف .py في backend/ ليعالج مخالفات flake8 التالية:
- W292: ملف بلا سطر جديد في نهايته
- W293/W291: سطر أخير يحوي مسافات فقط (يظهر بعد إضافة السطر الجديد)
- W391: أسطر فارغة زائدة في نهاية الملف
السبب: النسخ/اللصق (وبعض المحررات) يحذف السطر الأخير أو يترك مسافات في آخره.
النتيجة دائمًا: ينتهي الملف بسطر جديد واحد بالضبط. يحافظ السكربت على نوع
نهاية السطر الموجود (CRLF أو LF) ولا يمسّ أي شيء قبل النهاية.

الاستخدام (من داخل مجلد backend):
    poetry run python scripts/fix_eof_newline.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "env", "build", "dist", "migrations", "node_modules"}


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)


def fix_file(path: Path) -> bool:
    data = path.read_bytes()
    body = data.rstrip(b" \t\r\n")
    if not body:
        return False
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    fixed = body + newline
    if fixed == data:
        return False
    path.write_bytes(fixed)
    return True


def main() -> int:
    fixed = []
    for path in sorted(ROOT.rglob("*.py")):
        if _should_skip(path):
            continue
        if fix_file(path):
            fixed.append(path.relative_to(ROOT))

    if fixed:
        print(f"✅ نُظّفت نهاية {len(fixed)} ملف:")
        for p in fixed:
            print(f"   - {p}")
    else:
        print("✅ كل الملفات نهايتها سليمة بالفعل.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
