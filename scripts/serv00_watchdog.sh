#!/bin/sh
# Serv00 watchdog: keeps the bot process alive.
# Add to crontab (every 5 minutes):
#   */5 * * * * $HOME/quixote-dev-bot/scripts/serv00_watchdog.sh
set -u

DIR="$HOME/quixote-dev-bot"
PIDFILE="$DIR/bot.pid"
LOG="$DIR/bot.log"
PYTHON="$HOME/.venvs/quixote/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "[$(date '+%F %T')] ERROR: python not found at $PYTHON" >> "$LOG"
  exit 1
fi

if [ -f "$PIDFILE" ]; then
  pid=$(cat "$PIDFILE")
  if kill -0 "$pid" 2>/dev/null; then
    exit 0  # already running
  fi
  echo "[$(date '+%F %T')] stale pid $pid, restarting" >> "$LOG"
  rm -f "$PIDFILE"
fi

cd "$DIR"
echo "[$(date '+%F %T')] starting bot" >> "$LOG"
nohup "$PYTHON" -m src.quixote_bot.main >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
