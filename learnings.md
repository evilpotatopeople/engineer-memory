# Engineer Learnings

> 累積的工程決策教訓。由 /retro 和 /learn 追加。按時間倒序排列，最新的在最上面。
> 格式：日期 — 情境 — 學到什麼 — 下次怎麼改

---

## 2026-05-05 / DTC suite — offer SKU × 客群分析升級的 6 連 bug

詳細：`investigations/2026-05-05_offer_sku_segment_bug_chain.md`

- **欄位命名說謊是 schema 原罪、cohort `returning_customers` 含全部 1368 客（含新客）** — 這個 list 名是 `returning_customers`、語意上像是「老客名單」、但實際是「所有有 cohort 紀錄的客」、新/老靠 `act_class` 欄位區分（`新客` / `召回活躍` / `召回沉睡`）。寫 sheet 04 時直接把整個 list 當老客 → 訂單(老)全有、訂單(新)全 0。下次：1) 任何要分新/老客的程式必須讀 `act_class`、不能信 list 名；2) 跟 2026-04-28 「returning 語意不同」是同一個系統病、應該推動 cohort-analyzer 把 list 拆成 `new_customers` + `returning_customers` 兩個、徹底解決命名誤導。
- **JSON schema 不能憑記憶、要先 inspect** — sheet 04 的舊代碼讀 `promo_customers.json` 找 `customer_id` 跟 `is_new_customer` 欄位、實際 schema 是 `cid` 而且**根本沒有** `is_new_customer` 欄位。寫的時候沒 inspect、純粹幻覺。下次：1) 任何讀別人 JSON 的程式碼、PR review 必看「對應 producer 的寫入 code、確認 key 名一致」；2) ARCHITECTURE.md 的 schema 章節要列每個共享 .json 的欄位。
- **CSV line item 有 raw（含 ` xN`）跟 canonical（去尾）兩形態、target_skus 比對要 strip_qty** — 寫 helper 直接 `if r['原始字串'] in sku_set` 永遠 false、因為 raw line 帶 ` x1` 而 user 寫 target_skus 是 canonical name。`strip_qty` helper 早就存在、SOP 文檔沒提。下次：1) 把 `_canonical_line(r)` 包成單一 helper、所有 SKU 比對統一走它；2) SKILL.md 的 Step 2.2 註明 target_skus 寫 canonical（不含 ` xN`）+ 引用 `strip_qty` 規則。
- **canonical 化後所有 dict key 要一致、不可一處 raw 一處 canonical** — `sku_hit_count` 用 canonical 初始化、但 increment 用 raw key 拼錯、KeyError 把 offers.json 寫入炸了。下次：寫一個 `OfferHitTracker` class 把 SKU 比對 + 計數封裝、外部只看到 canonical 介面、避免某條路徑漏 strip。
- **v1→v2 schema 遷移要做整套、別留半截** — `offer_behavior.py` 升級 v2 (`target_categories` list) 後、舊 sheet writer 還讀 v1 (`target_category` string)、整欄顯示「-」、影響全 brand。下次：1) v2 遷移時、所有 reader 同時更新（grep 確認）；2) 留 fallback 給尚未升級的 caller（`v1_field or join(v2_field)`）；3) PR 描述要列「reader 清單」確保沒漏。
- **跨 list by-name join 必須有命名約定 SoT** — CAMPAIGN_OFFERS 寫「副軸-體驗組66折」、PROMO_CATEGORIES 寫「引流-體驗組66折」、相同 offer 兩個名字、`all_offer_names` set union 後變兩筆 record、metadata 跟 sheet07 數據掛不上。下次：1) SKILL.md 必須註明「CAMPAIGN_OFFERS.name 必須跟 PROMO_CATEGORIES.name 完全一致（如果同 offer 兩邊都列）」；2) promo_analyzer 在 dump offers.json 時加 audit、發現兩個 list 有相似名字但不完全相同就印 warning。

---

## 2026-04-28 / DTC suite spring2026 復盤 debug session

- **靜默 try/except 把 NameError 也吞掉、hook 從沒觸發** — `dtc-campaign-report/analyze.py` 的 brand_view sync hook 用了沒 import 的 `os.path.dirname`、`try: ... except Exception: pass` 把 NameError 吃掉、user 永遠看到 stale mirror 也不知道 hook 失效。下次：1) 不要包 `Exception`、要包具名 exception；2) hook 結尾一定印 ✅/⚠️ log、有 silent fail 看得到；3) 用既有的 Path 變數 (`AI_CLI`) 而不是現場拼 path。
- **schema 比對位置錯位、靜默無效** — `EXCLUDE_PRODUCT_KEYWORDS` 比對 `pfx`（line 切 `' - '` 前段）但 user 寫的 keyword 含規格 ` - 小盒，4條`、永遠 match 不到。設了 exclude 但保健肉泥滲透還是 90.3%、user 才發現。下次：1) schema 設計要明確說 keyword 要比對「完整 line / 主品名 / SKU 名」；2) 跑完做命中審計、0 命中印 warn（已寫 `_shared/audit_exclude_keywords.py`）。
- **同 flag 的 filter 套用不一致** — `納入分析='N'` 在 13 個 flat_rows iterator 裡只有 3 個有 filter、其他 10 個忽略、user 在不同 sheet 看到完全不同的「保健肉泥滲透」（02 是 90% / 05 也是 96%）。下次：1) 統一 helper（`_skip_sku_excluded`）、避免 copy-paste 漂移；2) 寫 audit 找 `for r in flat_rows` 沒 filter 的孤兒函式。
- **「returning」這個字在不同工具語意不同** — cohort 的 `returning_count` = 整檔下單客（含新客）、planner 的 `expected_returning_customers` = 老客回流預估、post_report 把兩個對接成「-69.5%」誤判爆表。實際拆開後 +1.9% 老客準、新客 -20% 才是真問題。下次：1) 跨工具的 schema 命名要 review、`recalled_count` / `new_count` 比 `returning_count` 精準；2) 對比邏輯要文檔說明分子分母概念、不能只看欄位名字。

---
