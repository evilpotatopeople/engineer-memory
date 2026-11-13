#!/usr/bin/env python3
"""記憶庫排程同步的「先拉再推」：business-memory／engineer-memory 兩支 sync 腳本提交完（或沒東西提交）後呼叫。

為什麼（帳本 T-0218-2）：兩台都在寫記憶庫。舊做法只在有新檔時 commit 後直接 push、錯誤丟掉，
另一台先推過就推不上去；之後工作區乾淨、整支直接結束，那筆 commit 永遠留在本機、沒人知道。

每一輪：
  1. git fetch origin
  2. 落後就跟上：本機沒有沒推的 commit → fast-forward；有 → rebase 到 origin/main 上
     （INDEX.md 兩台同時在最上方插一行很常見，repo 的 .gitattributes 設 merge=union，兩行都留）
  3. 有沒推的 commit 就 push
失敗不再丟掉，寫進 sync log；要人處理才在帳本開一件 --to human：
  - rebase／fast-forward 失敗（兩台改到同一段）：排程自己解不了，立刻開
  - fetch／push 失敗（網路、金鑰）：多半下一輪就好；最舊那筆沒推的 commit 放超過 2 小時才開
同一件事不重開；之後哪一輪推上去了，排程自己結案。
用法：memory-sync-remote.py <repo 名稱>     （在 repo 根目錄執行）
環境變數 MEMORY_SYNC_ALERT_AFTER_MIN 可改「放多久才開帳本」的分鐘數（測試用）。
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HAND = Path.home() / ".local/share/agent-ledger/current/bin/hand"  # 安裝版，跟 memory-commit-scan.py 同一支
STATE_DIR = Path.home() / "Library/Logs/memory-sync-remote"
BRANCH = "main"
ALERT_AFTER_SEC = int(os.environ.get("MEMORY_SYNC_ALERT_AFTER_MIN", "120")) * 60


def now():
    return time.strftime("%Y-%m-%d %H:%M")


def git(*args, timeout=120):
    """回傳 (成功與否, 合併後的輸出)。不丟例外：失敗由呼叫端決定要不要報。"""
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=off", *args], capture_output=True, text=True,
                           errors="replace", timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"})
    except subprocess.TimeoutExpired:
        return False, "逾時（%d 秒）" % timeout
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def tail(text, n=4):
    """log 用：git 的錯誤摘要。拿掉 hint: 那幾行說明，衝突時優先留 CONFLICT 那幾行（哪個檔）。"""
    lines = [s for s in text.splitlines() if s.strip() and not s.startswith("hint:")]
    picked = [s for s in lines if s.startswith("CONFLICT")] or lines
    return " | ".join(picked[-n:])[:400]


def count(rng):
    ok, out = git("rev-list", "--count", rng)
    return int(out) if ok and out.isdigit() else 0


def oldest_unpushed_age(upstream):
    ok, out = git("log", "--format=%ct", "%s..HEAD" % upstream)
    stamps = [int(s) for s in out.split() if s.isdigit()] if ok else []
    return time.time() - min(stamps) if stamps else 0


def machine_label():
    """帳本標題用：哪一台。用型號名（MacBook Air／MacBook Pro），不用電腦名稱（含人名）。"""
    try:
        out = subprocess.run(["/usr/sbin/system_profiler", "SPHardwareDataType"], capture_output=True,
                             text=True, timeout=30).stdout
        m = re.search(r"Model Name:\s*(.+)", out)
        if m:
            return m.group(1).strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "這台"


# ---- 帳本 ----

def hand(*args):
    try:
        return subprocess.run([sys.executable, str(HAND), *args, "--agent", "sync"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 99, "", str(e))


def load_state(repo):
    try:
        return json.loads((STATE_DIR / ("%s.json" % repo)).read_text())
    except (OSError, ValueError):
        return {}


def save_state(repo, data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / ("%s.json" % repo)).write_text(json.dumps(data, ensure_ascii=False))


def close_task(task, why):
    r = hand("done", task, "--evidence", why, "--source", "實測")
    print("  帳本：%s %s" % (task, "已結案" if r.returncode == 0
                            else "沒有結案（%s）" % (r.stderr or r.stdout).strip()[:120]))


def alert(repo, kind, title_reason, nxt):
    """kind=conflict 要人手動合併；kind=push 是網路或權限。同一種不重開；從 push 變成 conflict 才換一件。"""
    old = load_state(repo)
    if old.get("kind") == kind or (old.get("kind") == "conflict" and kind == "push"):
        print("  （帳本已有 %s 在追，這次不重開）" % old.get("task", ""))
        return
    r = hand("new", "%s（%s）自動同步推不上去：%s" % (repo, machine_label(), title_reason),
             "--to", "human", "--tag", "記憶庫同步",
             "--purpose", "記憶庫有紀錄只留在這台、還沒進 GitHub，要人處理",
             "--next", nxt[:290])
    if r.returncode != 0:
        print("  帳本任務開不了（rc=%d）：%s" % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
        return
    m = re.search(r"T-\d{4}(-\d+)*", r.stdout)
    task = m.group(0) if m else ""
    print("  帳本：開了 %s 給使用者" % (task or r.stdout.strip()[:80]))
    if old.get("task"):
        close_task(old["task"], "情況變了（%s），改由 %s 追" % (title_reason, task or "新任務"))
    save_state(repo, {"kind": kind, "task": task})


def recovered(repo, head):
    old = load_state(repo)
    if not old:
        return
    print("%s %s 先前推不上去的已經補上（HEAD %s）" % (now(), repo, head))
    if old.get("task"):
        close_task(old["task"], "下一輪排程已補推到 GitHub，本機沒有沒推的 commit（HEAD %s）" % head)
    (STATE_DIR / ("%s.json" % repo)).unlink(missing_ok=True)


# ---- 主流程 ----

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    repo = sys.argv[1]
    upstream = "origin/%s" % BRANCH
    log_hint = "~/Library/Logs/%s-sync.log" % repo

    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not ok or branch != BRANCH:
        print("%s %s 不在 %s 分支（現在：%s），這輪不同步" % (now(), repo, BRANCH, branch[:80]))
        alert(repo, "conflict", "不在 %s 分支" % BRANCH,
              "到那台 cd ~/Documents/%s，切回 %s（git switch %s）並確認沒有遺失的 commit；"
              "切回後下一輪排程會自己同步、這件也會自己結案。" % (repo, BRANCH, BRANCH))
        return 1
    ok, dirty = git("status", "--porcelain")
    if not ok or dirty:
        print("%s %s 工作區有還沒提交的改動，這輪先不拉不推（下一輪提交後再同步）" % (now(), repo))
        return 0

    fetched, out = git("fetch", "--quiet", "origin", BRANCH)
    if not fetched:
        print("%s %s fetch 失敗：%s" % (now(), repo, tail(out)))

    ahead, behind = count("%s..HEAD" % upstream), count("HEAD..%s" % upstream)
    if fetched and behind:
        if ahead:
            ok, out = git("rebase", upstream)
            step = "rebase"
        else:
            ok, out = git("merge", "--ff-only", upstream)
            step = "fast-forward"
        if not ok:
            if step == "rebase":
                git("rebase", "--abort")
            print("%s %s %s 到 GitHub 最新失敗（本機 %d 筆沒推、落後 %d 筆），已還原：%s"
                  % (now(), repo, step, ahead, behind, tail(out)))
            alert(repo, "conflict", "跟 GitHub 改到同一段",
                  "到那台 cd ~/Documents/%s 跑 git pull --rebase origin %s，手動解衝突（git status 看哪些檔）、"
                  "git rebase --continue 再 git push；推上去後下一輪排程會自己結這件。"
                  "解衝突期間排程會自己跳過，不會把衝突標記提交出去。" % (repo, BRANCH))
            return 1
        print("%s %s 已拉下 GitHub 新的 %d 筆（%s）" % (now(), repo, behind, step))
        ahead = count("%s..HEAD" % upstream)

    if ahead:
        ok, out = git("push", "--quiet", "origin", "HEAD:%s" % BRANCH)
        if ok:
            print("%s %s 已推 %d 筆" % (now(), repo, ahead))
            ahead = 0
        else:
            print("%s %s push 失敗（本機 %d 筆沒推）：%s" % (now(), repo, ahead, tail(out)))

    _, head = git("rev-parse", "--short", "HEAD")
    if fetched and not ahead:
        recovered(repo, head)
        return 0
    if not ahead:
        return 0  # fetch 失敗但本機沒東西要推：沒有東西會掉，下一輪再說

    age = oldest_unpushed_age(upstream)
    if age >= ALERT_AFTER_SEC:
        alert(repo, "push", "%d 筆放了 %.0f 小時" % (ahead, age / 3600),
              "看 %s 最後幾行的 fetch／push 錯誤（常見：網路、GitHub SSH 金鑰），排掉後下一輪排程會自己推、"
              "這件也會自己結案。" % log_hint)
    else:
        print("  （最舊那筆沒推的放了 %.0f 分鐘，未滿 %d 分鐘先不開帳本，下一輪重試）"
              % (age / 60, ALERT_AFTER_SEC // 60))
    return 1


if __name__ == "__main__":
    sys.exit(main())
