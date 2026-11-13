#!/bin/bash
# 每 30 分鐘跑一次，自動 commit engineer-memory 的變更，再跟 GitHub 先拉再推
# 安裝：bash ~/Documents/engineer-memory/setup/install-cron.sh（會一起把掃描器與同步程式複製到 ~/bin）
#
# 提交前先跑 memory-commit-scan.py（帳本 T-0220-2）：現場沒有 AI 也沒有人，
# 掃到疑似金鑰／個資就整批不提交、命中寫進這支的 log、在帳本開一件給使用者的任務；拿掉後下一輪自己提交。
# 提交後（或沒東西提交）跑 memory-sync-remote.py（帳本 T-0218-2）：先拉 GitHub 最新再推；
# 推不上去寫進這支的 log，兩台改到同一段或放太久才在帳本開任務給使用者，補上後自己結案。

REPO_NAME=engineer-memory
SCAN="${HOME}/bin/memory-commit-scan.py"
REMOTE="${HOME}/bin/memory-sync-remote.py"

cd ~/Documents/engineer-memory || exit 1

# 有人在手動解衝突（rebase／merge 做到一半）就整輪不碰，免得把衝突標記提交出去
GIT_DIR_PATH="$(git rev-parse --git-dir)"
if [ -d "${GIT_DIR_PATH}/rebase-merge" ] || [ -d "${GIT_DIR_PATH}/rebase-apply" ] || [ -f "${GIT_DIR_PATH}/MERGE_HEAD" ]; then
  echo "$(date '+%Y-%m-%d %H:%M') ${REPO_NAME} 有 rebase／merge 做到一半，這輪不動"
  exit 0
fi

if [ -n "$(git status --porcelain)" ]; then
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
fi

if [ ! -f "${REMOTE}" ]; then
  echo "$(date '+%Y-%m-%d %H:%M') 找不到 ${REMOTE}，這輪沒推（重跑 setup/install-cron.sh）"
  exit 1
fi
/usr/bin/python3 "${REMOTE}" "${REPO_NAME}"
