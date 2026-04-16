# CLAUDE.md — 工程決策記憶系統操作手冊

這份檔案是 **engineer-memory 系統的主控設定**。由 `~/.claude/CLAUDE.md` 引用，Claude Code 啟動時會讀到，用來覆寫 gstack 系列 skill 的寫入行為——把跑完的結論累積到持續記憶裡。

**適用範圍**：Claude Code 本機 session（不含 Cowork；Cowork 端由 business-memory 的 CLAUDE.md 處理）。

**設計原則**：本系統跟 business-memory 並列、互不干擾。`$MEMORY`（業務）和 `$ENGINEER_MEMORY`（工程）各自偵測、各自寫入。

---

## 一、記憶庫路徑偵測（供 gstack skill 在 Phase 0 引用）

當任一 gstack skill 啟動、執行到 Phase 0 時，用以下 bash 找 `$ENGINEER_MEMORY`：

```bash
# 依序找第一個存在的路徑
for p in \
  "$ENGINEER_MEMORY" \
  "$HOME/Documents/engineer-memory" \
  "$HOME/engineer-memory" \
  "./engineer-memory"
do
  if [ -n "$p" ] && [ -d "$p" ]; then
    echo "ENGINEER_MEMORY_FOUND=$p"
    break
  fi
done
```

**路徑對應**：

| 路徑 | 適用情境 |
|------|---------|
| `$ENGINEER_MEMORY` | 使用者自己設了環境變數 |
| `$HOME/Documents/engineer-memory` | **預設位置**（本機 clone） |
| `$HOME/engineer-memory` | 使用者做了 symlink |
| `./engineer-memory` | 當前資料夾下（少見） |

**找不到時的行為**：不要報錯、不要卡住、不要自己亂寫檔到別處。繼續正常對話，只在第一次適合的時機輕輕提一次：「你還沒建工程記憶庫，要照 `engineer-memory/setup/SETUP.md` 建嗎？」只提一次。

---

## 二、記憶庫載入時機（被觸發才載入，不預載）

> **教訓（2026-04-16 實測）**：Claude 不會因為 CLAUDE.md 寫「啟動即執行」就在純閒聊時自動跑 bash。這一節因此是「gstack skill 被觸發時 Phase 0 所用的路徑搜尋 + 記憶載入邏輯」。

**載入時機**：
1. 任一覆蓋清單（§ 四）的 gstack skill 啟動、Phase 0 找到 `$ENGINEER_MEMORY` 之後 → 立刻讀以下檔案
2. 使用者明確要求「給我看最近的工程決策/教訓/復盤」時 → 主動讀
3. 其他時候（純閒聊、商業討論、跟 engineer-memory 無關的工作）→ **不讀**

**載入內容**（觸發後跑這段 bash）：

```bash
# 1. 累積教訓（最重要，每次都讀）
cat "$ENGINEER_MEMORY/learnings.md" 2>/dev/null

# 2. 最近 3 份構想拷問
ls -t "$ENGINEER_MEMORY/ideas/" 2>/dev/null | grep -v '^\.' | head -3 | while read f; do
  echo "--- ideas/$f ---"
  cat "$ENGINEER_MEMORY/ideas/$f"
done

# 3. 最近 3 份工程復盤
ls -t "$ENGINEER_MEMORY/retros/" 2>/dev/null | grep -v '^\.' | head -3 | while read f; do
  echo "--- retros/$f ---"
  cat "$ENGINEER_MEMORY/retros/$f"
done

# 4. 最近 3 份計畫審查
for sub in ceo eng design; do
  ls -t "$ENGINEER_MEMORY/plans/$sub/" 2>/dev/null | grep -v '^\.' | head -2 | while read f; do
    echo "--- plans/$sub/$f ---"
    cat "$ENGINEER_MEMORY/plans/$sub/$f"
  done
done

# 5. 最近 3 份 investigation
ls -t "$ENGINEER_MEMORY/investigations/" 2>/dev/null | grep -v '^\.' | head -3 | while read f; do
  echo "--- investigations/$f ---"
  cat "$ENGINEER_MEMORY/investigations/$f"
done
```

**讀完後的回應**：

- 如果 learnings 或最近檔案**跟使用者當前話題有關**，主動把相關記憶帶進對話：
  > 「你之前在 {日期} 的 {主題} 學到 {教訓}——這次好像會撞到同個坑，要不要先處理？」
- 如果**無關**，不要主動展示「我讀了什麼」。記憶是背景知識，不是炫技。

**不要做的事**：
- 不要把整份 learnings.md 或記錄檔印出來給使用者看
- 不要每次 skill 啟動就說「我已載入記憶」
- 只在記憶**實際派上用場**時才提起

---

## 三、gstack skill 寫入行為（覆寫 Phase 6 / 結尾動作）

當覆蓋清單裡的 gstack skill 跑到結尾、準備給出結論時，**同步把結論寫進 engineer-memory**。

### 3.1 對應表（寫入位置）

| gstack skill | 寫入位置 | 是否追加到 learnings.md |
|-------------|---------|----------------------|
| `/office-hours` | `$ENGINEER_MEMORY/ideas/{YYYY-MM-DD}_{主題簡稱}.md` | 否 |
| `/plan-ceo-review` | `$ENGINEER_MEMORY/plans/ceo/{YYYY-MM-DD}_{主題簡稱}.md` | 否 |
| `/plan-eng-review` | `$ENGINEER_MEMORY/plans/eng/{YYYY-MM-DD}_{主題簡稱}.md` | 否 |
| `/plan-design-review` | `$ENGINEER_MEMORY/plans/design/{YYYY-MM-DD}_{主題簡稱}.md` | 否 |
| `/review` | `$ENGINEER_MEMORY/reviews/code/{YYYY-MM-DD}_{PR編號或主題}.md` | 否 |
| `/retro` | `$ENGINEER_MEMORY/retros/{YYYY-MM-DD}_{週期}.md` | **是** |
| `/investigate` | `$ENGINEER_MEMORY/investigations/{YYYY-MM-DD}_{bug簡稱}.md` | 條件性（見 3.3） |
| `/learn` | 整理 `$ENGINEER_MEMORY/learnings.md` | **是**（整理後覆寫） |

### 3.2 檔名規則

`{YYYY-MM-DD}_{主題簡稱}.md`

主題簡稱：最多 20 字、kebab-case 或中文都行、不能有 `/` 或空格。取自 skill 討論的核心主題（例如 `threads-scraper-mvp`、`dashboard-載入慢`）。

### 3.3 寫入內容格式（通用模板）

```markdown
# {主題} — {skill 名}
日期：{YYYY-MM-DD}
Skill：{gstack skill 名稱，例如 /retro}
狀態：[進行中 / 已結案 / 需後續追蹤]

## 摘要（一句話）
{本次 skill 最重要的結論}

## 詳細內容
{skill 的實際輸出原文，保留 markdown 格式}

## 後續動作
- [ ] {要做的事 1}
- [ ] {要做的事 2}

## 與過去的關聯
{如果 learnings.md 或過去記錄有相關，在此引用}
```

### 3.4 `/retro` 和 `/learn` 要追加 learnings.md

`/retro` 跑完：把「本週學到的 3 個教訓」追加到 `learnings.md` 最上方，格式：

```markdown
## {YYYY-MM-DD} / {週期}

- **{教訓 1 簡稱}** — {一句話描述，包含情境 + 下次怎麼改}
- **{教訓 2 簡稱}** — ...
- **{教訓 3 簡稱}** — ...
```

`/learn` 跑完：**消化整份 learnings.md**——合併重複、刪除過時、重新分類。寫回覆蓋原檔，但前面加一個 `## 整理紀錄` 區塊記下整理動作。

### 3.5 `/investigate` 的條件追加

只有當 bug 屬於以下類型時，才追加到 learnings.md：
- 踩過同一個坑 ≥ 2 次
- root cause 是設計層級的錯誤（不是 typo）
- 有教學意義、別的場景會重現

否則只寫 investigations 檔，不污染 learnings.md。

### 3.6 寫檔後必做

1. 在 `$ENGINEER_MEMORY/INDEX.md` 表格**最上方**插一行新紀錄：
   ```
   | {YYYY-MM-DD} | {type} | {主題} | {相對路徑} |
   ```
2. 告訴使用者寫到哪、檔名是什麼（一句話就好）
3. **不要**自己跑 `git commit`——cron 每 30 分鐘會自動處理

---

## 四、gstack skill 觸發規則（降低觸發模糊 + tiebreaker）

當使用者說出**工程相關關鍵字**時，**先在回應開頭一行明確宣告要啟動哪個 skill**，不要默默開始：

| 使用者語氣 | 啟動 skill | 開場白範例 |
|-----------|-----------|-----------|
| 「我有個技術構想」「這個架構要不要做」「值得寫嗎」 | `/office-hours` | 「這是還在構想階段的工程決策，我啟動 /office-hours 拷問。」 |
| 「幫我看這份工程計畫」「架構審一下」「技術方案有什麼漏洞」 | `/plan-eng-review` | 「你已經有成形的工程計畫，我啟動 /plan-eng-review 做壓力測試。」 |
| 「幫我看這份策略計畫」「商業層面審一下」 | `/plan-ceo-review` | 「這是商業策略計畫，啟動 /plan-ceo-review。」 |
| 「幫我 review 這段 code」「這個 PR 怎麼樣」 | `/review` | 「這是 code review，啟動 /review。」 |
| 「這週做了什麼」「做個工程復盤」「週報」 | `/retro` | 「這是工程週報復盤，啟動 /retro。」 |
| 「這個 bug 怎麼來的」「追一下這個問題的 root cause」 | `/investigate` | 「這是事故/bug 追蹤，啟動 /investigate。」 |
| 「整理一下我學到的教訓」「消化 learnings」 | `/learn` | 「這是 learnings 整理，啟動 /learn。」 |

### 模糊語句的 tiebreaker

| 使用者說 | 先問澄清 |
|---------|---------|
| 「幫我看一下這個」 | 是 code（→/review）、還是計畫（→/plan-eng-review）、還是構想（→/office-hours）？ |
| 「這個有什麼問題？」 | 是找 bug（→/investigate）、還是找設計漏洞（→/plan-eng-review）？ |
| 「復盤一下」 | 是工程週報（→/retro）還是某個 bug（→/investigate）？ |
| 「我想改善這個」 | 給我具體語境——是 code、架構、還是流程？ |

**不要兩個 skill 一起跑**。判斷不出時先問一句，不要硬猜。

---

## 五、不適用的情境（不要啟動 gstack skill）

- 使用者在做**商業決策、促銷、品牌策略、構想拷問**等主題 → 由 business-memory 的 skills 負責（`business-office-hours`、`ceo-plan-review`、`business-retro`），**本系統不介入**
- 使用者純閒聊、問事實性問題
- 使用者在處理 Cowork / Claude Code / 系統設定本身的問題（除非明確要求技術決策記錄）

**關鍵判準**：這句話是不是關於「工程決策、程式碼、架構、bug、系統行為」？如果不是，當普通對話處理。

---

## 六、跟 business-memory 的互動

這兩套系統**並行、不互通**：

| 維度 | business-memory | engineer-memory（本系統） |
|------|----------------|------------------------|
| 環境變數 | `$BUSINESS_MEMORY` / `$MEMORY` | `$ENGINEER_MEMORY` |
| 預設位置 | `~/Documents/business-memory/` | `~/Documents/engineer-memory/` |
| 適用 skill | `business-*`（anthropic-skills 體系） | `/office-hours`、`/plan-*`、`/review`、`/retro`、`/investigate`、`/learn`（gstack 體系） |
| 適用環境 | Cowork 為主 | Claude Code 本機 |
| GitHub repo | `business-memory`（private） | `engineer-memory`（private） |
| Cron 腳本 | `~/bin/business-memory-sync.sh` | `~/bin/engineer-memory-sync.sh` |

**例外**：如果某次討論**同時涉及**商業面和工程面（例如「要不要做 Threads 爬蟲做為新產品」），優先依據**使用者的切入角度**決定系統：
- 切入問「商業可行性、需求、市場」 → business-memory
- 切入問「技術架構、工程難度、選型」 → engineer-memory

需要 cross-reference 時，在該檔案結尾加一行：
> 相關：`$MEMORY/ideas/{對應檔案}.md` 或 `$ENGINEER_MEMORY/...`

---

## 七、這份檔案的維護

- **主檔**：`~/Documents/engineer-memory/CLAUDE.md`（git 追蹤，cron 自動 push）
- **被引用處**：`~/.claude/CLAUDE.md` 用 `@` 語法引用本檔
- **設計原則**：只寫「gstack 沒覆蓋到、或需要覆寫」的行為。不重複 gstack 各 skill SKILL.md 已有的內容
- **修改後**：本檔跟著 cron 自動 push 到 GitHub，不用手動管理
