#!/bin/bash
echo "Starting bot with mode: $RUN_MODE"

if [ "$RUN_MODE" = "bot" ]; then
  python main.py
elif [ "$RUN_MODE" = "clean" ]; then
  python clean_bot_data.py
else
  echo "Unknown RUN_MODE: $RUN_MODE"
  exit 1
fi
