#!/bin/bash
# 每 30 分鐘跑一次，自動 commit + push engineer-memory 變更到 GitHub
# 安裝：bash ~/Documents/engineer-memory/setup/install-cron.sh（會一起把掃描器複製到 ~/bin）
#
# 提交前先跑 memory-commit-scan.py（帳本 T-0220-2）：現場沒有 AI 也沒有人，
# 掃到疑似金鑰／個資就整批不提交、命中寫進這支的 log、在帳本開一件給使用者的任務；拿掉後下一輪自己提交。

REPO_NAME=engineer-memory
SCAN="${HOME}/bin/memory-commit-scan.py"

cd ~/Documents/engineer-memory || exit 1

if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

if [ ! -f "${SCAN}" ]; then
  echo "$(date '+%Y-%m-%d %H:%M') 找不到 ${SCAN}，這輪不提交（重跑 setup/install-cron.sh）"
  exit 1
fi

git add .
if ! /usr/bin/python3 "${SCAN}" "${REPO_NAME}"; then
  git reset -q    # 退回暫存，這輪什麼都不提交；下一輪重掃
  exit 1
fi

git commit -m "auto: $(date '+%Y-%m-%d %H:%M')" > /dev/null
git push origin main > /dev/null 2>&1
