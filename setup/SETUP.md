# Engineer Memory 安裝手冊

完整從零安裝或從 GitHub 回復 `engineer-memory` 的步驟。

---

## 情境 A：全新安裝（本機沒有 engineer-memory）

### 1. 前提條件

- macOS
- Claude Code 已安裝
- gstack skills 已安裝（通常在 `~/.claude/skills/gstack/`）
- bun 已裝並在 PATH 裡（`which bun` 要能找到）
- GitHub 帳號 + SSH key 已設好

### 2. 建立本地 repo

```bash
mkdir -p ~/Documents/engineer-memory/{ideas,plans/{ceo,eng,design},reviews/code,retros,investigations,setup,handoff}
cd ~/Documents/engineer-memory
git init -b main
```

### 3. 開 GitHub private repo

在 https://github.com/new 開一個叫 `engineer-memory` 的 **private** repo，**不要** initialize（不選 README / gitignore / license）。

### 4. 連 GitHub 並首次 push

```bash
cd ~/Documents/engineer-memory
git remote add origin git@github.com:<你的帳號>/engineer-memory.git
git add .
git commit -m "init: engineer-memory bootstrap"
git push -u origin main
```

### 5. 安裝 cron

```bash
bash ~/Documents/engineer-memory/setup/install-cron.sh
```

### 6. 設全域 CLAUDE.md

確認 `~/.claude/CLAUDE.md` 存在且引用了本系統：

```bash
grep "engineer-memory/CLAUDE.md" ~/.claude/CLAUDE.md
```

如果沒結果，手動加入：

```markdown
@~/Documents/engineer-memory/CLAUDE.md
```

---

## 情境 B：換電腦 / 從 GitHub 復原

### 1. Clone repo

```bash
git clone git@github.com:<你的帳號>/engineer-memory.git ~/Documents/engineer-memory
```

### 2. 確認 bun 安裝

```bash
which bun || curl -fsSL https://bun.sh/install | bash
```

如果裝完 `which bun` 還找不到，把下面寫進 `~/.zshenv`：

```bash
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
```

然後**重啟 Claude Code**（它用凍結的 shell snapshot，需要重啟才會更新 PATH）。

### 3. 安裝 cron

```bash
bash ~/Documents/engineer-memory/setup/install-cron.sh
```

### 4. 設全域 CLAUDE.md

```bash
mkdir -p ~/.claude
# 編輯 ~/.claude/CLAUDE.md，確保有這行：
# @~/Documents/engineer-memory/CLAUDE.md
```

或直接 clone 一份參考版本（如果 `~/.claude/` 本身也有放到 GitHub 的話）。

---

## 驗證

### V1：目錄跟 cron 都就位
```bash
test -d ~/Documents/engineer-memory/ideas && echo "✓ folders"
crontab -l | grep -q engineer-memory-sync && echo "✓ cron"
```

### V2：Git 連通
```bash
cd ~/Documents/engineer-memory && git remote -v | grep -q origin && echo "✓ remote"
git push --dry-run 2>&1 | grep -qE "Everything up-to-date|push" && echo "✓ push 可跑"
```

### V3：CLAUDE.md 被 Claude Code 讀到
開新的 Claude Code session（任意位置），問：
> 「你有讀到 engineer-memory 的 CLAUDE.md 嗎？寫入位置對應表的 /retro 應該寫到哪？」

Claude Code 應該能回答：`$ENGINEER_MEMORY/retros/{YYYY-MM-DD}_{主題}.md` 並追加到 `learnings.md`。

### V4：實際寫入
跑 `/office-hours` 一次，完成後檢查：
```bash
ls -lt ~/Documents/engineer-memory/ideas/ | head -3
head -5 ~/Documents/engineer-memory/INDEX.md
```

### V5：Cron 推到 GitHub
等 30 分鐘，或手動跑一次：
```bash
~/bin/engineer-memory-sync.sh
```

然後去 GitHub 看 commit log。

---

## 常見問題

### Q: `~/.claude/CLAUDE.md` 的 `@` include 不 work？
A: 確認路徑是絕對路徑、檔案存在、且 Claude Code 版本夠新。如果 `@` 語法不被支援，把 engineer-memory/CLAUDE.md 的內容**複製**到 `~/.claude/CLAUDE.md`（失去 DRY 但保證能 work）。

### Q: gstack skill 跑完沒寫進 engineer-memory？
A: 目前 v1 是「CLAUDE.md 軟規則」機制，不保證 100% 命中。觀察一週若漏太多，可加 Claude Code hook（PostToolUse 或 Stop）強制觸發寫入。

### Q: 兩套 memory 系統會不會打架？
A: 不會。路徑、環境變數、cron 腳本名、git repo 都不同。CLAUDE.md 也明確分工。
