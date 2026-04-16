#!/bin/bash
# 每 30 分鐘跑一次，自動 commit + push engineer-memory 變更到 GitHub
# 安裝：把此檔 symlink 或複製到 ~/bin/engineer-memory-sync.sh，chmod +x，加進 crontab

cd ~/Documents/engineer-memory || exit 1

if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

git add .
git commit -m "auto: $(date '+%Y-%m-%d %H:%M')" > /dev/null
git push origin main > /dev/null 2>&1
