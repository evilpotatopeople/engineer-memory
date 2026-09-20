# dashboard 跨裝置化（手機上看今天的數字）— /office-hours
日期：2026-09-21
Skill：/office-hours
狀態：已結案（設計 APPROVED，未動工）

## 摘要（一句話）
想讓 dashboard「正式化成軟體或網站」的真正瓶頸不是手機版面，是 tunnel 主機會跟人一起出門而且闔蓋就睡——所以解法是把數字推出去，不是把頁面做窄。

## 詳細內容

### 原始構想
使用者要讓 dtc 數據服務跨裝置可用：手機呼叫狀態、電腦端 AI 執行，並提到或許用 computer use。拆開是四件事，使用者排序 **A（手機看今天數字）> B（壞掉主動通知）> C（外面叫電腦跑）> D（手機上跟 AI 討論）**。服務對象只有使用者自己。

### 本輪最重要的發現
`pmset -g log` 實測：**闔蓋在插電時照樣 Clamshell Sleep**（09-19 11:30、09-20 02:39 兩筆都是 Using AC）。tunnel 跑在每天帶出門的 MBP 上，通勤掏手機那一刻機器正闔著蓋，`dash.shepherdtechboard.com` 回 502。所以手機版面做得再好都沒用。

四條便宜解逐條否決：`pmset -b disablesleep 1`（過熱＋耗電，耗盡照樣打不開）、WoL（電池下 womp 0 且外網無 L2 路徑）、`caffeinate -i`（擋不了闔蓋）、Cloudflare 快取（Streamlit 靠 WebSocket，快取到外殼是死頁）。**收下一個對自己不利的框架：本方案本質上是手工版的 Always Online。**

### 誠實的降級
推送本身也跑在同一台會睡的機器上。闔蓋時 launchd 只在下次醒來補跑一次，不是每個錯過的小時各補；1-45 秒的 DarkWake 窗口會切斷 job。**所以承諾是「看到上次筆電醒著時的數字、且明確標示那是幾點」，不是「今天的數字」。**

### 選定方案：E → C，分三階段
- **階段 0（必須先拍板）**：管道選型（決定 LINE Messaging API——使用者是重度 LINE 使用者，`LINE.MediaService` assertion 持有超過 100 小時；LINE Notify 已於 2025-03-31 停服）；非檔期的「對基準」怎麼辦（決定只送絕對數字並明說無基準）。
- **階段 1｜推播**（~2.5-3 天）：定內容 → 定時區 → 組裝腳本（唯讀取用 analytics）→ **口徑對帳** → 推送（帶 hostname + 資料截至 + 產生時間）→ postback 按鈕量測 → LaunchAgent 對齊 :42 + `pmset repeat wake` 兩週實測 → token 放 `~/.config/dtc/` 600 不進版控。
- **閘門**：兩週內「看過了」≥5 次且「想看更細」≥1 次 → 做階段 2；沒過**停在階段 1**（不是整個停掉，階段 1 順帶交付 B 的一半）。
- **階段 2｜靜態頁 + 登入**（不可拆）：選 Pages 或 R2 → `today` 子網域 → Zero Trust Access **session 設一個月等級** → **禁令：新頁不得放 `static/` 或走 `/component/`**（不經 auth 閘）→ 白名單 sync → 停滯門檻 >3h 黃 / >12h 紅 → 訊息帶連結要注意**第三個 cookie jar**（通訊軟體內建瀏覽器 ≠ Safari ≠ standalone PWA，會重觸發 OTP）→ 狀態放遠端不放本機。
- **階段 3｜iOS 加入主畫面**（可選，有退路）。

### 兩輪對抗性審查（6/10 → 7/10）
第一輪抓到：推送鏈死在同一個坑、少了「推播」這一整格方案、P2 與選定方案矛盾、OQ 與 Distribution Plan 互相打臉。
第二輪抓到：**非檔期沒有基準來源**（`intraday.py` grep `baseline|ref|yoy` 零命中、實跑 `dtc read today` 輸出也確認無基準欄位；只有檔期的 `status.json` 帶基準——兩個源覆蓋互斥時段）、閘門不可判定（bot 沒有已讀狀態）、雙跑鎖在通訊軟體 API 上沒有 primitive（改成偵測：訊息帶 hostname，收到兩則就知道雙跑）。**另誤報一條（`dtc` 不存在），已實跑推翻。**

### 審查誤判、經實跑推翻的一條
第二輪審查斷言「`dtc` 指令不存在」，因為它只查了 PATH 與 `~/bin`。**實際存在且可跑**：`./_shared/runtime/dtc read today [--store <店>]`（帶路徑執行）。2026-09-21 實跑 lm_tw 回 JSON 正常。**教訓：查「指令存不存在」只查 PATH 是不夠的，帶路徑的 wrapper 查不到。**

順帶撿到：該輸出已內建 `as_of` / `age_minutes` / `verdict`，**停滯判斷不必自己寫門檻**，直接用 `verdict`。

### 被否決的
**computer use**：每件事都有 CLI，用截圖點自己的 CLI 是十倍成本換十分之一可靠度。除非出現真的沒 API 的對象（BI 後台、蝦皮數據中心）才回頭談。
**「軟體 vs 網站」二選一**：固定網址 + iOS 加入主畫面就同時是兩者，不用送審。

### C/D 不需要開發
Claude Code 桌面版內建 Remote Control，開關打開就能從手機 App 或 claude.ai/code 接管本機 session。前置一樣是常駐主機。

## 後續動作
- [ ] 階段 0-1：開 LINE Developers 帳號 + Messaging API channel（1-2 小時）
- [ ] 階段 0-2 已決：非檔期只送絕對數字
- [ ] 階段 1 步驟 1：手寫列出通勤時真的想看的三到五個數字
- [ ] **優先序高於本案**：雙跑防護從檢查表升級成機制（兩台機器都會保留安裝，雙跑是常態風險不是遷移陷阱）

## 與過去的關聯
- `ideas/2026-09-19_跨agent交接帳本.md`：本案是該文件 Premise 5 排定的第二階段，但**否決其原定手段**（「沿用現有 tunnel 與登入」）——tunnel 就是瓶頸。
- `ideas/2026-08-05_mac-mini自架伺服器.md`：Premise 6 的紅線（個人基礎設施＋受控 pilot）沿用；該文件把雙跑當一次性遷移陷阱處理，本輪確認是常態風險。
- `investigations/2026-09-09_daily-sync-lm_tw-缺一天.md`：同一個 clamshell sleep 根因的另一半。
- 設計文件全文：`~/.gstack/projects/Claudetest/hsuyutong-main-design-20260921-012217.md`

### 2026-09-21 補充：常駐主機已排程，階段 2 要重評估
使用者表示 Air 扶正**近兩週內要跟組員一起建置**。這與階段 1 的閘門日幾乎重疊。

若 Air 在閘門日前後上線，**階段 2（靜態頁＋Zero Trust）存在的最大理由就消失了**——主機不睡、tunnel 永遠通。屆時 **Approach B（Streamlit 手機優先頁）反而勝出**：~2 天 vs ~3-4 天、不用子網域／託管／ZT／token、**資料完全不離開本機**、`auth.py` 的閘自動套用。

閘門日的判斷順序：先問「Air 上線了嗎」，再問「階段 1 閘門過了嗎」。兩者皆是 → 做 Approach B。

另需連帶釐清：組員參與建置後，這台機器還算不算 2026-08-05 Premise 6 的「個人基礎設施」。屬伺服器專案範圍。

帳本：agent-ledger **I-0028**（七則 office-hours 結論已記入）。
