#!/bin/bash
echo "Starting bot with mode: $RUN_MODE"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python interpreter not found."
  exit 1
fi

if [ "$RUN_MODE" = "bot" ]; then
  exec "$PYTHON_BIN" main.py
elif [ "$RUN_MODE" = "clean" ]; then
  exec "$PYTHON_BIN" utils/clean_bot_data.py
else
  echo "Unknown RUN_MODE: $RUN_MODE"
  exit 1
fi
