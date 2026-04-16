# 工程決策記憶庫

由 gstack skills（/office-hours、/plan-*-review、/review、/retro、/investigate、/learn）在 Claude Code 本機跑完時自動維護。

與 business-memory 並列，兩套系統**各管各的**，互不干擾。

---

## 🆘 換電腦了？

1. 新電腦裝好 Claude Code + gstack
2. `git clone git@github.com:<username>/engineer-memory.git ~/Documents/engineer-memory`
3. 確認 `~/.claude/CLAUDE.md` 有引用這個目錄的 CLAUDE.md（看 `setup/SETUP.md`）
4. 安裝 cron：`setup/install-cron.sh`

完整步驟見 [`setup/SETUP.md`](setup/SETUP.md)。

---

## 結構

- `ideas/` — `/office-hours` 的構想拷問紀錄
- `plans/ceo/` — `/plan-ceo-review` 的輸出
- `plans/eng/` — `/plan-eng-review` 的輸出
- `plans/design/` — `/plan-design-review` 的輸出（未來啟用）
- `reviews/code/` — `/review` 的程式碼審查報告
- `retros/` — `/retro` 的工程週報復盤
- `investigations/` — `/investigate` 的 bug / 事故 root cause 分析
- `learnings.md` — 所有 retro 濃縮的核心教訓（`/learn` 負責整理消化）
- `INDEX.md` — append-only 時間軸目錄
- `setup/` — 環境備份（sync 腳本、SETUP.md、install-cron.sh）
- `handoff/` — 跨機器/跨人交接文件

## 自動同步

Mac 上每 30 分鐘 cron 會跑 `~/bin/engineer-memory-sync.sh`，把變更自動 commit + push 到這個 private repo。

## 跟 business-memory 的分工

| 主題 | 去哪 |
|------|------|
| 商業決策、促銷、產品構想 | `~/Documents/business-memory/` |
| 工程決策、code review、bug 追蹤、工程週報 | `~/Documents/engineer-memory/`（本 repo） |

如果某筆記兩邊都適用，寫在**主導視角**那邊，另一邊用 cross-reference 連過來。
