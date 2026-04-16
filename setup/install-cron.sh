#!/bin/bash
# 安裝 engineer-memory 的 cron sync job
# 執行：bash ~/Documents/engineer-memory/setup/install-cron.sh

set -e

# 1. 複製 sync 腳本到 ~/bin
mkdir -p ~/bin
cp ~/Documents/engineer-memory/setup/engineer-memory-sync.sh ~/bin/engineer-memory-sync.sh
chmod +x ~/bin/engineer-memory-sync.sh
echo "✓ Installed ~/bin/engineer-memory-sync.sh"

# 2. 確保 log 目錄存在
mkdir -p ~/Library/Logs

# 3. 加入 crontab（若尚未存在）
CRON_LINE="*/30 * * * * \$HOME/bin/engineer-memory-sync.sh >> \$HOME/Library/Logs/engineer-memory-sync.log 2>&1"
if crontab -l 2>/dev/null | grep -q "engineer-memory-sync"; then
  echo "✓ Cron job already installed"
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  echo "✓ Added cron job (runs every 30 min)"
fi

echo ""
echo "Verify:"
echo "  crontab -l | grep engineer-memory"
echo "  tail -f ~/Library/Logs/engineer-memory-sync.log"
