#!/bin/bash
set -euo pipefail

cd /app

mkdir -p databases storage/uploads storage/resources storage/question_banks

# 首次启动：建表 + 管理员（init_admin 幂等）
python - <<'PY'
from app.core.database import init_databases
init_databases()
print("Database tables ready.")
PY

python init_admin.py || true

exec "$@"
