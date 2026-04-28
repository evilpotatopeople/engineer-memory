# Engineer Learnings

> 累積的工程決策教訓。由 /retro 和 /learn 追加。按時間倒序排列，最新的在最上面。
> 格式：日期 — 情境 — 學到什麼 — 下次怎麼改

---

## 2026-04-28 / DTC suite spring2026 復盤 debug session

- **靜默 try/except 把 NameError 也吞掉、hook 從沒觸發** — `dtc-campaign-report/analyze.py` 的 brand_view sync hook 用了沒 import 的 `os.path.dirname`、`try: ... except Exception: pass` 把 NameError 吃掉、user 永遠看到 stale mirror 也不知道 hook 失效。下次：1) 不要包 `Exception`、要包具名 exception；2) hook 結尾一定印 ✅/⚠️ log、有 silent fail 看得到；3) 用既有的 Path 變數 (`AI_CLI`) 而不是現場拼 path。
- **schema 比對位置錯位、靜默無效** — `EXCLUDE_PRODUCT_KEYWORDS` 比對 `pfx`（line 切 `' - '` 前段）但 user 寫的 keyword 含規格 ` - 小盒，4條`、永遠 match 不到。設了 exclude 但保健肉泥滲透還是 90.3%、user 才發現。下次：1) schema 設計要明確說 keyword 要比對「完整 line / 主品名 / SKU 名」；2) 跑完做命中審計、0 命中印 warn（已寫 `_shared/audit_exclude_keywords.py`）。
- **同 flag 的 filter 套用不一致** — `納入分析='N'` 在 13 個 flat_rows iterator 裡只有 3 個有 filter、其他 10 個忽略、user 在不同 sheet 看到完全不同的「保健肉泥滲透」（02 是 90% / 05 也是 96%）。下次：1) 統一 helper（`_skip_sku_excluded`）、避免 copy-paste 漂移；2) 寫 audit 找 `for r in flat_rows` 沒 filter 的孤兒函式。
- **「returning」這個字在不同工具語意不同** — cohort 的 `returning_count` = 整檔下單客（含新客）、planner 的 `expected_returning_customers` = 老客回流預估、post_report 把兩個對接成「-69.5%」誤判爆表。實際拆開後 +1.9% 老客準、新客 -20% 才是真問題。下次：1) 跨工具的 schema 命名要 review、`recalled_count` / `new_count` 比 `returning_count` 精準；2) 對比邏輯要文檔說明分子分母概念、不能只看欄位名字。

---
