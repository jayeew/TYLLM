#!/usr/bin/env bash
set -euo pipefail

# 本地脚本触发入口：不启动 FastAPI，直接执行库存预警/补货预测任务。
# 默认优先使用项目虚拟环境；如果没有 .venv，则使用当前 PATH 中的 python。
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="${PYTHON:-python}"
fi

exec "$PYTHON_BIN" -m app.tasks.local_runner "$@"
