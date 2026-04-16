# Claude Code Handoff — Engineer Memory System

> **給 Claude Code 讀的**。使用者（Dugald）已經在 Cowork 這邊建好了 business-memory 系統（商業決策記憶層），現在要請你把同樣的架構移植到 gstack（Garry Tan 的 Claude Code 工程 skill 套件）上，建立 engineer-memory。
>
> **執行流程**：
> 1. 讀完這整份文件（特別是 Part 4 的血淚教訓）
> 2. 執行 Part 7 的「開工前必問」——問完再動手
> 3. 跑 Part 8 的實作步驟
> 4. 按 Part 9 的驗證標準自我檢查

---

## Part 0：一分鐘總覽

- **使用者已安裝 gstack**（https://github.com/garrytan/gstack），Claude Code 本機能跑 `/office-hours`、`/plan-ceo-review`、`/retro`、`/review`、`/ship` 等 23 個 skill
- **gstack 沒有記憶層**——skill 跑完，結論散落在各自 session，沒有持續累積的 `learnings.md` 或決策檔案
- **使用者已經在 Cowork 上蓋好 business-memory**，那套設計驗證過有效、也踩過坑，現在要把**同一套記憶層 pattern** 套到 gstack 的工程 skill 上
- **你的任務**：建 `engineer-memory` 資料夾 + CLAUDE.md 覆寫層 + cron git sync，讓 gstack 的 `/office-hours`、`/plan-*-review`、`/retro` 等 skill 跑完後把結論寫進持續記憶
- **不要動 gstack 本身**（upstream 別人維護的 repo，改下去會跟上游衝突）

---

## Part 1：business-memory 長什麼樣（你的藍圖）

### 1.1 目錄結構

```
~/Documents/business-memory/
├── CLAUDE.md                    # 覆寫層主控檔（最重要）
├── INDEX.md                     # append-only 紀錄表，每寫一個檔新增一行
├── learnings.md                 # 累積教訓，retro 結束時追加
├── ideas/                       # business-office-hours 的輸出
│   └── 2026-04-16_貓砂訂閱制構想.md
├── plans/                       # ceo-plan-review 的輸出
├── retros/                      # business-retro 的輸出
├── handoff/                     # 本文件就放這裡
├── setup/
│   ├── SETUP.md                 # 初次安裝手冊
│   ├── skills/                  # 4 個客製 SKILL.md 的 source of truth
│   │   ├── business-office-hours/SKILL.md
│   │   ├── ceo-plan-review/SKILL.md
│   │   ├── business-retro/SKILL.md
│   │   └── business-memory-init/SKILL.md
│   ├── deploy-skills.sh         # 把 skills/ 同步到 Cowork 會用到的兩個位置
│   ├── verify-skills-in-sync.sh # md5 三方比對
│   └── bin/
│       └── business-memory-sync.sh  # cron 跑的 git auto-push
└── .git/                        # GitHub private repo
```

### 1.2 GitHub sync 機制

- 主機 cron：每 30 分鐘跑 `~/Documents/business-memory/setup/business-memory-sync.sh`
- 腳本做的事：`cd` 進 repo → 若沒變動 exit → 否則 `git add .` + `git commit -m "auto: <timestamp>"` + `git push origin main`
- SSH key 認證（不是 PAT），直接能 push private repo
- Cron line 長這樣（可能透過 `~/bin/` 下的 symlink 調用）：
  ```
  */30 * * * * $HOME/bin/business-memory-sync.sh >> $HOME/Library/Logs/business-memory-sync.log 2>&1
  ```

### 1.3 skill 寫入行為

這 4 個 business-* skill 的 SKILL.md 裡，Phase 6（結尾）都被覆寫成：

- `business-office-hours` → 寫一份 markdown 到 `$MEMORY/ideas/{YYYY-MM-DD}_{主題簡稱}.md`
- `ceo-plan-review` → 寫到 `$MEMORY/plans/...`
- `business-retro` → 寫到 `$MEMORY/retros/...` 並**追加教訓到 `$MEMORY/learnings.md`**
- 寫完後必做：在 `$MEMORY/INDEX.md` 表格最上方插一行新紀錄

---

## Part 2：四層觸發機制架構（重要！engineer-memory 要複製）

這是 business-memory 最關鍵的設計。**觸發「不是一層，是四層」**：

### 第 1 層：SKILL.md frontmatter `description`（硬觸發）
- 系統層比對使用者輸入 vs description 關鍵字，選最像的 skill 觸發
- **這層不可覆寫**，是 Claude 系統底層決定的
- 設計時要讓 description 關鍵字**互斥**——避免同一句話觸發多個 skill

### 第 2 層：SKILL.md 的 Phase 流程（skill 內部執行）
- skill 被觸發後，Claude 讀完整 SKILL.md，按 Phase 0 → 1 → 2... 走
- **只要 skill 觸發、這層必定會跑**

### 第 3 層：CLAUDE.md 覆寫指令（軟規則）
- CLAUDE.md 被灌進 system prompt，Claude 讀到當作「規則知識」
- Claude **不會主動執行** CLAUDE.md 裡的 bash code，只會在判斷需要時參考
- 可以做到：
  - 使用者講關鍵字 → 提醒 Claude 用特定開場白宣告啟動哪個 skill
  - 模糊輸入 → tiebreaker 規則叫 Claude 先問澄清
  - skill 跑到 Phase 6 → 遵守寫入位置規則
- **做不到**：session 啟動自動跑偵測、主動預載記憶

### 第 4 層：hook / 啟動腳本（技術機制，目前沒用）
- Claude Code 有 hook 機制（SessionStart 等），可以強制執行 bash
- business-memory 目前沒用這一層
- engineer-memory 如果想實現「進 gstack repo 自動載入 engineer-memory」，**這一層是唯一可靠的路**

---

## Part 3：最關鍵的血淚教訓（2026-04-16 實測）

### 教訓 A：CLAUDE.md 的「啟動即執行」是無效設計
- 原本設計 CLAUDE.md § 一寫「每次 session 啟動先跑 Phase 0 bash」
- **實測結果：不會跑**。Claude 是 reactive，打招呼時判斷「不需要工具」就不動
- **對 engineer-memory 的意義**：不要在 CLAUDE.md 寫「session 啟動自動 X」——要嘛接受「skill 觸發時才跑」，要嘛走 Claude Code hook

### 教訓 B：description 關鍵字容易重疊
- 原本 `business-office-hours` description 說「『這個活動怎麼樣』觸發」
- `promotion-designer` description 說「『這個活動怎麼樣』都應觸發此 Skill」
- 兩個搶同一句話，Claude 系統層判斷不穩定
- **修復方式**：description 改用「階段 × 層級」矩陣，每個 skill 佔一格不重疊，並明確寫「明確不用於 X（用 sibling-skill-name）」
- **對 engineer-memory 的意義**：如果未來設計多個 engineer-memory skill（或 gstack skill 之間有衝突），用同樣的紀律避開

### 教訓 C：三份 SKILL.md 位置會 drift
- business-memory 場景有三份：git repo / Cowork 專案 .claude/skills / plugin temp
- **engineer-memory 場景不一樣**：只會有 `~/.claude/skills/` 或 gstack repo 內，不會有三份
- 但**維護仍要注意**：改 gstack upstream 以外的任何 skill 時，要想清楚放在哪、誰是 source of truth

### 教訓 D：tiebreaker 是最後一道安全網
- 就算 description 設計很小心，總有使用者說「幫我看看這個」這種模糊輸入
- CLAUDE.md 的 § 四 tiebreaker 救了這個——Claude 判斷不出時先問一句
- **對 engineer-memory 的意義**：CLAUDE.md 必須寫 tiebreaker 表，把常見模糊語列出來、怎麼澄清

### 教訓 E：記憶不預載、被觸發才載
- 原本設計「session 啟動把 learnings.md 塞進腦袋」——無效
- **實測有效版**：skill 被觸發時讀 learnings.md + 最近 3 份記錄
- 不預載其實更乾淨——純閒聊時記憶不污染對話

---

## Part 4：business-memory 的 CLAUDE.md 原文（最終版）

**位置**：`~/Documents/business-memory/CLAUDE.md`

engineer-memory 的 CLAUDE.md 用這份當模板，按需要改內容但**結構保持一致**。原文見本 repo 的 `/CLAUDE.md`（跟這份 handoff 文件同個 repo）。

重點結構：

```
## 一、記憶庫路徑偵測（供 skill 在 Phase 0 引用）
## 二、記憶庫載入時機（被觸發時載入，不預載）
## 三、skills 寫入行為（覆寫 Phase 6）
## 四、Skill 觸發規則（降低觸發模糊 + tiebreaker）
## 五、不適用的情境
## 六、這份檔案的維護
```

---

## Part 5：與 gstack 的關係

### gstack 有的 skill（別改它們）

依照 2026-04-16 repo 狀態：`/office-hours`、`/plan-ceo-review`、`/plan-eng-review`、`/plan-design-review`、`/design-consultation`、`/design-shotgun`、`/design-html`、`/review`、`/ship`、`/land-and-deploy`、`/canary`、`/benchmark`、`/browse`、`/connect-chrome`、`/qa`、`/qa-only`、`/design-review`、`/retro`、`/investigate`、`/document-release`、`/codex`、`/cso`、`/autoplan`、`/plan-devex-review`、`/devex-review`、`/careful`、`/freeze`、`/guard`、`/unfreeze`、`/gstack-upgrade`、`/learn`

### 跟 business-memory 對位

| gstack | business-memory 對應 | 建議 engineer-memory 子資料夾 |
|--------|-------------------|-------------------------|
| `/office-hours` | business-office-hours | `ideas/`（構想期拷問） |
| `/plan-ceo-review` | ceo-plan-review | `plans/ceo/` |
| `/plan-eng-review` |（無對應） | `plans/eng/` |
| `/plan-design-review` |（無對應） | `plans/design/` |
| `/review` |（無對應，代碼審查） | `reviews/code/` |
| `/retro` | business-retro | `retros/` |
| `/learn` |（consolidate-memory 類似） | 觸發 `learnings.md` 整理 |
| `/investigate` |（無對應，bug 追蹤） | `investigations/` |

### 要解決的基本問題

gstack skill 跑完不會寫進記憶。你要：
1. **不修改 gstack 的 SKILL.md**（upstream 的）
2. 在 gstack 專案根目錄 / 或 `$HOME/.claude/CLAUDE.md` 寫覆寫層，指揮 Claude Code：「跑完 `/office-hours`、`/retro` 等 skill 後，順手把產出寫進 `$ENGINEER_MEMORY/ideas/` 等位置」
3. 選項 B：用 Claude Code 的 hook（PostToolUse 或類似），在 skill 結束時觸發寫入腳本——更可靠但 hook 語法要查

---

## Part 6：engineer-memory 的目標

### 成功狀態

1. 使用者在 Claude Code 跑 `/office-hours` 或 `/retro` 後，對應記錄自動寫進 `$ENGINEER_MEMORY` 對應資料夾
2. `learnings.md` 會在每次 `/retro` 或 `/learn` 之後累積教訓
3. `INDEX.md` 維持 append-only 紀錄
4. cron 每 30 分鐘 git push 到 GitHub private repo
5. 下次 session 跑 gstack skill 時，Claude Code 會先載入 learnings.md 當背景知識
6. 如果跑 business-* skill（在 Cowork 裡），兩套記憶系統**不互相干擾**（$MEMORY 和 $ENGINEER_MEMORY 各自偵測）

### 非目標（不要做）

- ❌ 修改 gstack 的任何檔案（upstream 維護）
- ❌ 把 business-memory 跟 engineer-memory 合成一個 repo
- ❌ 用 hook 強制 session 啟動就執行 bash（除非使用者明確要求，且有心理準備要維護 hook）

---

## Part 7：開工前必問使用者的問題

**先把這 6 題問完再動手**。使用者已說明 engineer-memory 的部分他還沒決定，所以需要你主動釐清：

1. **engineer-memory 實體位置**？
   - 選項 A：`~/Documents/engineer-memory/`（跟 business-memory 並列）
   - 選項 B：`~/code/gstack/.engineer-memory/`（貼在 gstack repo 旁邊）
   - 選項 C：`~/code/engineer-memory/`（獨立 repo）
   - 我的建議：**A**，理由是跟 business-memory 對稱、分開兩個 repo 避免互相污染

2. **GitHub 要新開 private repo 嗎？repo 名建議什麼？**
   - 建議 `engineer-memory`（跟 business-memory 命名對稱）
   - 需要使用者在 GitHub 先開好、給你 SSH URL

3. **覆蓋哪些 gstack skill**？全部 23 個，還是只挑幾個常用的？
   - 建議先挑：`/office-hours`、`/plan-ceo-review`、`/plan-eng-review`、`/review`、`/retro`、`/investigate`、`/learn`
   - 其他上線後再加

4. **CLAUDE.md 放哪裡？**
   - 選項 A：`$HOME/.claude/CLAUDE.md`（全 Claude Code session 都會讀，影響範圍大）
   - 選項 B：gstack repo 根目錄 `CLAUDE.md`（只在那個 repo 有效，但使用者可能不只在一個 repo 用 gstack）
   - 選項 C：每個工作 repo 獨立放 `CLAUDE.md`（最乾淨但要重複部署）
   - 建議：**A**（全域），因為 gstack 是工程工作流，不綁特定專案

5. **記憶載入時機**：採用 business-memory 的「被觸發才載入」設計，還是試走 Claude Code hook 實現「session 啟動自動載入」？
   - 建議：**先走「被觸發才載入」**。Hook 之後可以加，但一開始保守
   - 如果使用者想試 hook，要準備好除錯時間

6. **`/learn` skill 的接入**：gstack 有個 `/learn` skill，功能疑似就是「整理教訓」。要不要把它設計成寫入 `learnings.md`？
   - 建議：是。這樣 `/retro` + `/learn` 各自有職責——retro 寫單次復盤，learn 做整理消化

---

## Part 8：實作步驟（使用者回答完 Part 7 後執行）

### Step 1：建立資料夾

```bash
# 假設使用者選了 Part 7 Q1 的選項 A
mkdir -p ~/Documents/engineer-memory/{ideas,plans/{ceo,eng,design},reviews/{code},retros,investigations,setup/bin,handoff}
cd ~/Documents/engineer-memory
git init
```

### Step 2：寫 CLAUDE.md（engineer-memory 主控檔）

位置：`~/Documents/engineer-memory/CLAUDE.md`

直接抄 `~/Documents/business-memory/CLAUDE.md` 結構，換名字：

- `$MEMORY` → `$ENGINEER_MEMORY`
- `business-*` skills → gstack 的 `/office-hours`、`/plan-*`、`/review`、`/retro` 等
- 路徑偵測改成找 `~/Documents/engineer-memory/`（不要跟 business-memory 互相干擾）
- 觸發表改成工程語氣
- tiebreaker 改成工程情境的模糊語（例如「幫我看一下這個」→ 是 code review 還是 eng-plan-review？）

### Step 3：寫 `~/.claude/CLAUDE.md`（全域覆寫）

位置：`$HOME/.claude/CLAUDE.md`（如果使用者選 Part 7 Q4 選項 A）

這份是 **Claude Code 啟動時一定會讀** 的檔案。內容：

1. 引用 `~/Documents/engineer-memory/CLAUDE.md` 的細節（用 `@file` 語法，Claude Code 支援 `@path` include）
2. 寫死 gstack skill → engineer-memory 寫入位置的對應表
3. 注意：不要跟 business-memory 衝突——這份 CLAUDE.md 只在 Claude Code（主機端）生效；business-memory 的 CLAUDE.md 在 Cowork 工作資料夾生效

示意：
```markdown
# Global Claude Code CLAUDE.md — Engineer Memory Integration

## Engineer Memory 系統

@~/Documents/engineer-memory/CLAUDE.md

## gstack skill 寫入規則

| gstack skill | 寫入位置 | 追加教訓 |
|-------------|---------|---------|
| /office-hours | $ENGINEER_MEMORY/ideas/{date}_{topic}.md | 否 |
| /plan-ceo-review | $ENGINEER_MEMORY/plans/ceo/{date}_{topic}.md | 否 |
| /retro | $ENGINEER_MEMORY/retros/{date}_{topic}.md | **是**（追加到 learnings.md） |
| /learn | 整理 $ENGINEER_MEMORY/learnings.md | 整理後 git commit |
...

## 注意事項
- 如果正在 Cowork 工作資料夾（有 business-memory CLAUDE.md），優先遵守那份
- 本 CLAUDE.md 只管 Claude Code 本機執行時的 engineer-memory 行為
```

### Step 4：初始化 learnings.md、INDEX.md

```bash
cat > ~/Documents/engineer-memory/learnings.md << 'EOF'
# Engineer Learnings

> 累積的工程決策教訓。每次 /retro 或 /learn 之後追加。
> 格式：日期 — 情境 — 學到什麼 — 下次怎麼改

---

EOF

cat > ~/Documents/engineer-memory/INDEX.md << 'EOF'
# Engineer Memory INDEX

| Date | Type | Topic | File |
|------|------|-------|------|

EOF
```

### Step 5：設 cron git sync

```bash
cat > ~/Documents/engineer-memory/setup/engineer-memory-sync.sh << 'EOF'
#!/bin/bash
cd "$HOME/Documents/engineer-memory" || exit 1
if [ -z "$(git status --porcelain)" ]; then exit 0; fi
git add .
git commit -m "auto: $(date '+%Y-%m-%d %H:%M')" > /dev/null
git push origin main > /dev/null 2>&1
EOF
chmod +x ~/Documents/engineer-memory/setup/engineer-memory-sync.sh

# 加進 crontab
( crontab -l 2>/dev/null ; echo "*/30 * * * * $HOME/Documents/engineer-memory/setup/engineer-memory-sync.sh >> $HOME/Library/Logs/engineer-memory-sync.log 2>&1" ) | crontab -
```

### Step 6：GitHub private repo

```bash
# 假設使用者已用 gh CLI 登入
gh repo create engineer-memory --private --source=. --remote=origin --push
# 或手動：使用者在 github.com 開好 repo，然後
git remote add origin git@github.com:<username>/engineer-memory.git
git branch -M main
git push -u origin main
```

### Step 7：第一次試跑

讓使用者在 Claude Code 跑一次 `/office-hours`，看 Claude Code 會不會：
1. 讀到 `~/.claude/CLAUDE.md`
2. 跑 `/office-hours` 六道問題
3. 結束時寫一份 markdown 到 `~/Documents/engineer-memory/ideas/`
4. 更新 `INDEX.md`

如果沒寫進去，檢查：
- `~/.claude/CLAUDE.md` 的 include 語法（`@file` 是否被支援）
- 對應表寫得夠不夠明確
- 參考 business-memory 的 CLAUDE.md § 三寫入規則

---

## Part 9：驗證標準（跑完自我檢查）

依序跑這 5 個測試，全過才算完成：

### 驗證 1：目錄跟 cron
```bash
test -d ~/Documents/engineer-memory/ideas && echo "✓ 目錄" || echo "✗ 目錄"
crontab -l | grep -q engineer-memory-sync && echo "✓ cron" || echo "✗ cron"
```

### 驗證 2：git 連通
```bash
cd ~/Documents/engineer-memory && git remote -v | grep -q origin && echo "✓ git remote"
git push --dry-run 2>&1 | grep -qE "Everything up-to-date|push" && echo "✓ git push 可跑"
```

### 驗證 3：CLAUDE.md 被讀
開一個新的 Claude Code session（在任意位置），問：「你有讀到 engineer-memory 的 CLAUDE.md 嗎？」——如果 Claude Code 回答具體內容（例如能複述觸發表的某幾行），代表有。

### 驗證 4：硬觸發 + 寫入
在 Claude Code 跑 `/office-hours`，走完六道問題，確認：
- `~/Documents/engineer-memory/ideas/` 多了一份新 markdown
- `~/Documents/engineer-memory/INDEX.md` 最上方多了一行

### 驗證 5：cron 推到 GitHub
等 30 分鐘（或手動跑 `engineer-memory-sync.sh`），然後：
```bash
cd /tmp && git clone git@github.com:<username>/engineer-memory.git /tmp/em-verify
ls /tmp/em-verify/ideas/  # 應該看到剛才 /office-hours 產的檔
rm -rf /tmp/em-verify
```

---

## Part 10：未來維護的建議

### 不要做的事
- ❌ 不要 fork gstack 改它的 SKILL.md（升級會衝突）
- ❌ 不要把 business-memory 和 engineer-memory 合一（主題混雜會讓觸發模糊）
- ❌ 不要在 Cowork 工作資料夾也放 engineer-memory 的 CLAUDE.md（那是 Claude Code 的事）

### 要做的事
- ✅ 使用者有新的 gstack skill 要接入時，只改 `~/.claude/CLAUDE.md` 的對應表
- ✅ gstack upgrade 後要重新測一次 skill 名稱跟觸發關鍵字有沒有變
- ✅ 每季跑一次 `consolidate-memory` 整理 `learnings.md`（Cowork 有這個 skill）

### 未解決問題（留給未來）
- Hook 機制：如果想實現「session 啟動自動預載 learnings.md 到對話」，要研究 Claude Code 的 SessionStart hook。business-memory 沒用這條路，因為 Cowork 側沒有對應 hook。
- engineer-memory 跟 business-memory 的 `learnings.md` 互相學習：如果某個工程教訓也適用於商業決策（或反過來），要不要有機制 cross-reference？目前沒做。
- 團隊共享：如果未來使用者要把 engineer-memory 給團隊用，private repo 的 access control 和 merge 流程要重新設計。

---

## 附錄 A：關鍵檔案路徑快查

| 檔案 | 路徑 | 用途 |
|------|------|------|
| business-memory CLAUDE.md | `~/Documents/business-memory/CLAUDE.md` | 商業記憶覆寫層（**你的參考範本**） |
| business-memory cron 腳本 | `~/Documents/business-memory/setup/business-memory-sync.sh` | git auto-push 參考實作 |
| business-memory SKILL.md 例 | `~/Documents/business-memory/setup/skills/business-office-hours/SKILL.md` | 看 Phase 0/6 怎麼寫 |
| business-memory deploy script | `~/Documents/business-memory/setup/deploy-skills.sh` | （engineer-memory 不一定需要） |
| gstack 本身 | 使用者已用 gstack 的安裝腳本裝好，位置可問使用者 | 參考 skill 名稱對應 |

## 附錄 B：使用者環境資訊

- **User name**：dugald
- **Email**：d1u2g3a4l5d6@gmail.com
- **主機**：macOS
- **已安裝**：Claude Desktop + Cowork mode、Claude Code、gstack（via Claude Code）
- **既有 cron**：business-memory 已有一條，每 30 分鐘跑
- **SSH key**：已經設好給 GitHub private repo 用（business-memory 用這把）

## 附錄 C：跟使用者的對話風格

使用者是商業決策者（非工程師背景但懂）。溝通時：
- 直接說結論，不要廢話繞圈
- 技術選項要給建議（不要全丟給他選）
- 失敗或卡住時誠實說「不知道」或「不能確定」——不要瞎猜
- 中文對話，繁體中文（台灣）

---

## 結尾

讀完整份文件後，**先把 Part 7 的 6 題一次問完**（建議用清單形式一次呈現，不要一題一題問）。收到答案後按 Part 8 執行，按 Part 9 驗證。有卡住或不確定的，回來查 Part 3 的血淚教訓——很可能已經踩過。

祝順利。

— Cowork Claude，於 2026-04-16
