# daily sync lm_tw 靜默缺一天 — /investigate
日期：2026-09-09
Skill：/investigate（事故追蹤＋架構評估；未跑完整 skill 對話流程，依 engineer-memory §3 格式落檔）
狀態：需後續追蹤

## 摘要（一句話）
lm_tw 09-08 整天沒進 master／DuckDB 而 pipeline 回報綠燈：直接原因是「這次抓不完整」這個事實只存在 log 文字裡、沒接到 Stage 1b 與通知；根本原因是整條 pipeline 跑在會蓋蓋子睡覺的日常筆電（MacBook Pro M5 Pro）上，兩支排程整晚只在 DarkWake 的幾秒鐘有進度——不是 Metorik、也不是兩個 job 搶 API。

## 詳細內容

### 時間線
- 03:08 daily sync 起跑（排 03:00；launchd 在 DarkWake 補跑）
- heromama_tw 03:08–07:26：13 次 Connection reset、Page 17 partial（1,600 筆）→ master 停 09-06 → Stage 1b 判 stale（< today-2）→ 10:32 retry 成功
- lm_tw 08:32–10:18：DNS NameResolution 失敗、Page 5 partial（400 筆）→ refresh_master_data 30% 守門「要刪 94.9%、restate 放棄」→ master +0、停 09-07 → **Stage 1b cutoff = today-2 = 09-07、不小於、不 retry**；check_dashboard_freshness 同樣 < 2 天判定 → 「全店 OK、桌面警告檔已清」
- 10:16:54 機器 FullWake → 其餘 5 店 10:18–10:27 全部正常
- 10:44–10:59 DuckDB rebuild 用了缺一天的 master；10:57 user 手動 `sync_orders.py lm_tw --auto-merge` 補回 +417；DuckDB 另跑 `backfill_from_csv --brand lm --market tw` 才跟上
- 走速盤 01:17 那輪跑到 10:20（dcs build 24,778 s、lm 7,748 s），吃掉 02:12–10:12 共 9 次觸發；lm 報表帶「fetch 失敗、沿用上一次」、generated 停在 00:32

### 根因
1. **睡眠**：`pmset -g log` 顯示 09-08 23:17 起 Clamshell Sleep、電池供電，每 ~15 分 DarkWake 2–45 秒，直到 09-09 10:16:54 FullWake。兩份 log 每個時間戳（00:23、01:17、03:08、07:26、07:55、08:10、08:32、10:18）都對上一次 DarkWake。`caffeinate -i` 只擋 idle sleep、擋不了 clamshell。Connection reset／DNS 失敗是睡醒瞬間網路未接回的症狀（今天 0 次 429、全 log 歷史只 3 次）。
2. **partial 訊號沒接線**：fetcher 遇分頁失敗只 `warnings.add(...)` 然後回 partial rows；sync_orders exit 0；refresh_master_data 的 30% 守門只 print、exit 0。Stage 1 因此算成功、Stage 1b 只能靠日期推論、通知走「完成 11 店」。同一個事實在三層都被丟掉。
3. **日期 heuristic 的兩難**：cutoff today-2 是 2026-06-16（commit 8a3ba9a）為容忍稀疏店設的；aqua_hk 近 60 天有 37 天零訂單，改 today-1 會每兩天誤報一次（各 5 分鐘 sleep＋retry）。日期永遠分不出「沒單」和「沒抓到」。
4. **runner timeout 睡眠盲**：`BUILD_TIMEOUT=1200` 靠 `subprocess.run(timeout=)`（monotonic clock），macOS 睡眠時不走，24,778 s 的 build 照樣「成功發布」。

### 兩條修法的架構評估

**A. Stage 1b 抓不到「只缺一天」的店 → 推進，但不是改 cutoff**
- 正確修法：把「已知的 partial」變結構化訊號一路傳到 retry 與通知；日期 heuristic 留作 backstop。
- **已有半成品**：`.claude/worktrees/infallible-matsumoto-5cdcb0`（branch `claude/busy-blackburn-76e1c6`、**未 commit**）— 9/2 事故 task chip 的產物：`FetchOutcome`（partial／failed_page／complete_through_tw_date）、`safe_restate_window`（partial 時 restate 窗尾縮到保證完整日 −1）、23 個測試（0.03 s 全綠）、`run_checks.sh` 掛入。今天驗證：分岐點 71b378e 之後 main 沒動這 4 支檔，`git apply --check` 乾淨。
- WIP 解的是 9/2（誤刪）；**還沒解 9/9（靜默落後）**：exit code 不變、不寫 marker、Stage 1b 與通知都沒接。缺的約 20 行：sync_orders 在 `outcome.partial` 時 exit 3；refresh_master_data 30% 守門觸發時 exit 3；sync_all_daily Stage 1 把 rc=3 收進 `partial[]`（不算 failed）；Stage 1b retry `stale ∪ partial`；retry 後仍 partial 的店進「降級」通知。
- 影響面：`sync_orders.py` 呼叫者只有 sync_all_daily.sh 兩處＋smoke test（只測 `--help`）；手動 `&&` 串接會在 partial 時停下——這是想要的行為。

**B. 走速盤讓路機制 → 不做**
- 前提「兩個 job 搶 API」不成立（0 次 429；兩邊都是被凍住）。讓路／preemption 對今天零幫助。
- runner 既有設計（build 或 fetch 失敗 → published 沿用上一版、status.json 標 generated 與 warnings）在今天是**正確地降級**，不是 bug。
- 唯一小缺陷是 timeout 睡眠盲；可選低優先修法：round 層加 wall-clock 上限（`datetime.now()` 對 round 起點 > N 分就放棄剩餘 build），讓睡醒的舊輪次不要在 10 小時後才「發布」。機器不睡的前提下這條沒有價值。
- 真正對應的修法是 **2026-08-05 已拍板的專職伺服器計畫**：排程器不該跟日常機同一台，遷移日清單裡本來就有「pmset 常開」。今天 pipeline 跑在 MacBook Pro M5 Pro（日常機）上；`com.user.dtc-daily-sync` / `com.dtc.refresh` plist 的 mtime 是 May 25 / Jun 18（看起來像 Migration Assistant 帶過來），`com.dtc.pace-hourly` / `com.dtc.cloudflared` 是 Sep 5 / 7 在這台新建——橋接方案「MBP 到手先卸 com.dtc.* plist、Air 轉專職伺服器」的執行狀態要 user 確認，含 Air 是否還掛同一組 plist 的雙跑風險。

### 決策（建議）
1. **推進 A**：先把 worktree WIP 套上 main（乾淨、已有測試），再接「partial → exit 3 → Stage 1b／通知」那 20 行並補一個 Stage 1b 測試。兩個獨立 commit，半天內。
2. **不做 B 的讓路機制**；timeout 改 wall-clock 列為可選。
3. **今晚起營運止血**：pipeline 所在機器夜間插電＋不蓋蓋子（或 `pmset disablesleep`、需 sudo、user 自己下）。否則 A 修完照樣會有 partial（只是會被 retry 救回）。
4. **策略層**：今天列為已拍板伺服器計畫 Phase 0/2 的事故證據；優先確認 Air 的 plist 狀態。
5. **不做**：cutoff 改 today-1；共用 fetch 層重構；`caffeinate -i` 改 `-is`（對 clamshell／電池無效）。

## 後續動作
- [x] A-1：2026-09-09 11:41 完成 — worktree patch（7 檔）＋測試檔收進 `feat/metorik-fetcher` **`7f9fee8`**；pre-commit 四段全綠（pattern audit／golden 200 鎖定值／drift 0／23 tests）；未 push、未 merge main。另一 session 同時段 commit 了 `823f6e2`（campaign_review 版面），無衝突
- [ ] A-2：partial → exit 3（sync_orders／refresh_master_data；**不能用 2、argparse 參數錯誤已佔 2**）；sync_all_daily Stage 1 收 rc=3 進 partial[]、Stage 1b retry stale ∪ partial、通知列 partial 店；補測試
- [ ] 營運：確認 pipeline 主機夜間供電與 lid 狀態；確認 Air 上 `launchctl list | grep dtc` 是否仍有 com.dtc.* / com.user.dtc-daily-sync（雙跑）
- [ ] 可選：runner round 層 wall-clock 上限
- [ ] WIP 合進 main 後移除 `.claude/worktrees/infallible-matsumoto-5cdcb0`
- [ ] cosmetic：sync_all_daily 訊息「全 8 店」→ 實際店數

## 與過去的關聯
- 2026-09-02 lm_tw restate 誤刪 8/31 尾段——同 trigger（DNS → partial）；那次的 task chip 就是這份 WIP。記錄在 Claude auto-memory `project_sync_restate_partial_fetch_deletes_rows`
- 2026-06-16 commit 8a3ba9a「三層防護應對週期性 DNS transient 失敗」——Stage 1b／cutoff today-2／check_dashboard_freshness 的出生點；當時 5/29、6/13-14、6/16 的「週期性 DNS 失敗」很可能同樣是睡眠造成、被當成網路問題處理
- learnings「silent-fail 家族」（05-05、05-06、08-07、09-07）——這次是第 7 例：失敗被印在沒人讀的 log、上層回報成功
- 2026-08-05 /office-hours Mac mini：「痛的本質是單點依賴」、「排程漏跑、idle-sleep 中斷補 caffeinate」正是今天

相關：`$ENGINEER_MEMORY/ideas/2026-08-05_mac-mini自架伺服器.md`
