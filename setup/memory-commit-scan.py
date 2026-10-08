#!/usr/bin/env python3
"""排程提交前的機密掃描：business-memory／engineer-memory 兩支 sync 腳本在 git add . 之後、commit 之前呼叫。

現場沒有 AI 也沒有人，所以掃到不能只是失敗（帳本 T-0220-2）：
  - exit 0：乾淨，可以提交
  - exit 1：掃到東西，不要提交。命中印到 stdout（sync 腳本導到 ~/Library/Logs/<repo>-sync.log）
  - exit 2：掃描器自己壞了（載不到樣式、git 失敗），一樣不要提交
1、2 第一次發生時在帳本開一件 --to human 的任務，hand status 的「要使用者本人處理的」看得到；
同一批命中下一輪不再重開，恢復乾淨後清掉記錄，下次再擋才會再開。

掃什麼：git diff --cached 的新增行（就是這次會提交的內容）＋新增或改動的檔名。
  - 金鑰：直接載入已安裝帳本 bin/hand 的 SECRET_PATTERNS，不另寫一套
  - 整類檔案不准進：訂單／客戶匯出常見的資料檔、憑證檔
  - email、台港手機號碼：純比對會誤判，但這兩個資料夾只放筆記，寧可擋下來等人看；
    確定沒問題的字串寫進 repo 根目錄的 .commit-scan-allow（一行一個）
用法：memory-commit-scan.py <repo 名稱>             掃 index（sync 腳本用）
      memory-commit-scan.py <repo 名稱> --all --dry  掃所有已追蹤檔、不碰帳本（試誤判用）
git@github.com、noreply 署名、這個 repo 的 git user.email 一律放行。
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HAND = Path.home() / ".local/share/agent-ledger/current/bin/hand"  # 安裝版，不讀別人正在改的工作複本
STATE_DIR = Path.home() / "Library/Logs/memory-commit-scan"
BLOCKED_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".parquet", ".duckdb", ".db", ".sqlite", ".jsonl",
               ".pem", ".key", ".p12", ".pfx"}
BLOCKED_NAME = re.compile(r"(^|/)(\.env(\..*)?|id_(rsa|ed25519|ecdsa)|credentials[^/]*|.*secret[^/]*\.json)$", re.I)
ALWAYS_ALLOW = ["git@github.com", "noreply@anthropic.com", "noreply@github.com"]  # SSH 遠端、commit 署名
PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}\b")),
    ("台灣手機號碼", re.compile(r"(?<!\d)(\+?886[\- ]?9|09)\d{2}[\- ]?\d{3}[\- ]?\d{3}(?!\d)")),
    ("香港電話（含 +852）", re.compile(r"\+?852[\- ]?[2-9]\d{3}[\- ]?\d{4}(?!\d)")),
]


def load_secret_patterns():
    loader = importlib.machinery.SourceFileLoader("hand_installed", str(HAND))
    spec = importlib.util.spec_from_loader("hand_installed", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    pats = list(mod.SECRET_PATTERNS)
    if not pats:
        raise RuntimeError("SECRET_PATTERNS 是空的")
    return pats


def git(*args):
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], check=True,
                          capture_output=True, text=True, errors="replace", timeout=60).stdout


def staged_lines():
    """(檔名, 行號, 內容)：這次會提交的新增行。"""
    out, path, lineno = [], None, 0
    for raw in git("diff", "--cached", "--no-color", "--no-ext-diff", "-U0", "--diff-filter=d").splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            out.append((path, lineno, raw[1:]))
            lineno += 1
    return out


def all_lines():
    out = []
    for path in git("ls-files", "-z").split("\0"):
        if not path or not Path(path).is_file():
            continue
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        out.extend((path, i, line) for i, line in enumerate(text.splitlines(), 1))
    return out


def scan(paths, lines, secret_pats, allow):
    hits = []
    for p in paths:
        if Path(p).suffix.lower() in BLOCKED_EXT or BLOCKED_NAME.search(p):
            hits.append((p, 0, "這類檔案不准進（資料匯出或憑證）"))
    for path, n, line in lines:
        for a in allow:  # 只拿掉允許的那段字，同一行其他東西照掃
            line = line.replace(a, " ")
        for name, pat in secret_pats:
            if pat.search(line):
                hits.append((path, n, "像「%s」" % name))
        for name, pat in PII_PATTERNS:
            if pat.search(line):
                hits.append((path, n, "像個資（%s）" % name))
    return hits  # 只記位置與種類，不把命中的字串本身寫進 log 或帳本


def hand(*args):
    return subprocess.run([sys.executable, str(HAND), *args, "--agent", "sync"],
                          capture_output=True, text=True, timeout=60)


def close_task(task, why):
    """排程自己開的任務排程自己收；使用者已經手動結掉的，結不了就算了。"""
    r = hand("done", task, "--evidence", why, "--source", "實測")
    print("  帳本：%s %s" % (task, "已結案" if r.returncode == 0 else "沒有結案（%s）" % (r.stderr or r.stdout).strip()[:120]))


def alert(repo, title_reason, detail, key, dry):
    """第一次遇到這批命中才在帳本開一件給使用者的任務；同一批不重開，換了一批就收掉舊的、開新的。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    mark = STATE_DIR / ("%s.json" % repo)
    try:
        old = json.loads(mark.read_text())
    except (OSError, ValueError):
        old = {}
    if old.get("key") == key:
        print("  （同一批命中已經開過帳本任務 %s，這次不重開）" % old.get("task", ""))
        return
    if dry:
        print("  （--dry：不開帳本任務）")
        return
    nxt = ("看 ~/Library/Logs/%s-sync.log 最後一段，拿掉或改寫命中的內容（誤判就把字串加進 .commit-scan-allow），"
           "下一輪 sync 就會自己提交，這件也會自己結案。%s" % (repo, detail))[:290]
    r = hand("new", "%s 排程提交被擋：%s" % (repo, title_reason), "--to", "human", "--tag", "機密防線",
             "--purpose", "記憶庫自動同步停了，要人確認是不是真的機密再放行", "--next", nxt)
    if r.returncode != 0:
        print("  帳本任務開不了（rc=%d）：%s" % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
        return
    m = re.search(r"T-\d{4}(-\d+)*", r.stdout)
    task = m.group(0) if m else ""
    print("  帳本：開了 %s 給使用者" % (task or r.stdout.strip()[:80]))
    if old.get("task"):
        close_task(old["task"], "命中的內容換了一批，改由 %s 追" % (task or "新任務"))
    mark.write_text(json.dumps({"key": key, "task": task}))


def clear(repo):
    mark = STATE_DIR / ("%s.json" % repo)
    if not mark.exists():
        return
    try:
        task = json.loads(mark.read_text()).get("task")
    except (OSError, ValueError):
        task = None
    print("%s %s 先前的擋下已解除，這次掃描乾淨、照常提交" % (time.strftime("%Y-%m-%d %H:%M"), repo))
    if task:
        close_task(task, "下一輪排程重掃乾淨，已照常提交")
    mark.unlink()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    repo, full, dry = sys.argv[1], "--all" in sys.argv, "--dry" in sys.argv
    try:
        secret_pats = load_secret_patterns()
        allow_file = Path(".commit-scan-allow")
        allow = [s.strip() for s in allow_file.read_text(encoding="utf-8").splitlines()
                 if s.strip() and not s.startswith("#")] if allow_file.exists() else []
        allow += ALWAYS_ALLOW + [e for e in [git("config", "user.email").strip()] if e]  # 自己的 email 不算個資
        if full:
            lines = all_lines()
            paths = [p for p in git("ls-files", "-z").split("\0") if p]
        else:
            lines = staged_lines()
            paths = [p for p in git("diff", "--cached", "--name-only", "-z", "--diff-filter=d").split("\0") if p]
        hits = scan(paths, lines, secret_pats, allow)
    except Exception as e:  # 掃描器壞了也不能放行
        print("%s %s 掃描器出錯，這輪不提交：%s: %s" % (time.strftime("%Y-%m-%d %H:%M"), repo, type(e).__name__, e))
        alert(repo, "掃描器出錯", "錯誤：%s" % type(e).__name__, "error:" + type(e).__name__, dry)
        return 2
    if not hits:
        if not dry:
            clear(repo)
        return 0
    print("%s %s 掃到 %d 處疑似機密或個資，這輪不提交：" % (time.strftime("%Y-%m-%d %H:%M"), repo, len(hits)))
    for path, n, why in hits:
        print("  %s%s：%s" % (path, ":%d" % n if n else "", why))
    files = sorted({h[0] for h in hits})
    key = hashlib.sha256(json.dumps(sorted({(h[0], h[2]) for h in hits}), ensure_ascii=False).encode()).hexdigest()[:16]  # 不含行號：改到別行不重開
    alert(repo, "疑似機密或個資（%d 處）" % len(hits),
          "命中的檔：%s" % "、".join(files[:3]) + ("等 %d 個" % len(files) if len(files) > 3 else ""), key, dry)
    return 1


if __name__ == "__main__":
    sys.exit(main())
