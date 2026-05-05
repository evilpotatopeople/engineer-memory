# offer SKU × 客群分析升級的 6 個 bug 鏈 — /investigate

日期：2026-05-05
Skill：手動記錄（非 /investigate 自動觸發）
狀態：已結案、code 已加防呆

## 摘要（一句話）
新增 `level_offer_sku_segment` helper 把 `target_skus` 接進 SKU 級客群分析時、連續踩了 6 個 bug、root cause 全是「不同 JSON / data layer 的 schema 默契不一致」、值得未來實作類似分析時引以為戒。

## 任務脈絡
- spring2026_tw 11 個 offer 走完案型對焦 SOP、補 target_skus
- 發現 sheet01 / sheet04 大量空白
- 評估後選方案 A：promo_analyzer 新增 SKU × 客群指標、寫進 offers.json/metric_by_segment、offer_behavior 加最高優先 source `sheet07_v2_sku`
- 過程踩 6 個 bug、全部修完 + regression（HM 20/20）通過

## 踩過的 6 個 bug（按出現順序）

### Bug 1 — `target_category` 顯示「-」
**症狀**：sheet01 整欄「-」、影響全 brand 全 campaign。
**根因**：`_shared/offer_behavior.py` line 484 build common dict 時、只塞 `target_categories` (v2 list) 沒塞 `target_category` (v1 string fallback)。Sheet writer 讀 v1 欄位 → KeyError → 顯示「-」。
**修法**：common dict 加 `'target_category': offer_meta.get('target_category') or '/'.join(target_categories)`。
**教訓**：v1→v2 遷移時、sheet writer 跟 dataset 的 schema 同步要做完整、否則「升級了一半」。

### Bug 2 — CAMPAIGN_OFFERS vs PROMO_CATEGORIES 命名衝突
**症狀**：副軸-體驗組66折 metric_source=none、訂單空白。但 PROMO_CATEGORIES「引流-體驗組66折」其實 sheet07 命中 425 訂單。
**根因**：兩個 list 都列同一個 offer、但前綴不同（「副軸-」 vs 「引流-」）→ `all_offer_names` set union 後變成 2 筆 record、metadata 跟 sheet07 數據掛在不同 key 上。
**修法**：把 CAMPAIGN_OFFERS 改名跟 PROMO_CATEGORIES 對齊。
**教訓**：跨 list 共用 by-name join 時、命名約定要寫進 SKILL.md 的 SOP、否則每個 user 各寫各的。

### Bug 3 — target_skus match 0（quantity suffix）
**症狀**：寫好 helper、跑完所有 offer SKU_hit=0/N。
**根因**：CSV line item 帶 ` xN` quantity suffix（例：`...每日口腔 x1`）、user 在 config 寫 target_skus 是 canonical name（去尾巴）、直接 `if r['原始字串'] in sku_set` 永遠 false。
**修法**：用既存的 `strip_qty(line)` helper、line_canonical 後再比對。
**教訓**：line item 字串有兩種形態（raw with qty / canonical）、要在 doc 說清楚 target_skus 該寫哪種。`strip_qty` 已是公開 helper、應在 SOP 文檔註明。

### Bug 4 — `sku_hit_count` key 拼錯
**症狀**：`offers.json 輸出失敗：'...每日免疫 x1'`、KeyError。
**根因**：`sku_hit_count = {sku: 0 for sku in sku_set}` 用 canonical key 初始化、但 increment 寫 `sku_hit_count[line]` 用 raw key（含 x1）。
**修法**：改 `sku_hit_count[line_canonical]`。
**教訓**：canonical 化後、所有 dict access 都要用 canonical key。寫一個 `_canonical_line(r)` 一次到位的 helper、避免某些路徑漏 strip。

### Bug 5 — promo_customers.json 沒帶客群
**症狀**：sheet04「訂單(新)/(老)」全 0。
**根因**：sheet04 寫入時讀 `promo_customers.json` 找 `customer_id` / `is_new_customer` 欄位、但實際 schema 是 `cid` 而且**根本沒有** `is_new_customer` 欄位。`new_old_map` 永遠空。
**修法**：改讀 `dtc-cohort-analyzer/outputs/{key}_customers.json`（cohort 端）。
**教訓**：schema 要有單一 SoT（source of truth）、而且 ARCHITECTURE.md 必須列出每個 .json 的欄位。憑記憶寫 `is_new_customer` 是純粹幻覺。

### Bug 6 — cohort json `returning_customers` 不是「老客」
**症狀**：修完 bug 5 後、訂單(新) 還是 0、訂單(老) 變全部。
**根因**：`returning_customers` list **包含全部 1368 客**、不是「只有老客」。要看 `act_class` 欄位（`新客` / `召回活躍` / `召回沉睡`）才能正確分類。命名極度誤導。
**修法**：iterate `returning_customers`、用 `act_class` 判斷。
**教訓**：欄位命名說謊、是 schema 設計的原罪。`returning_customers` 應改名 `all_customers_with_history`、或拆成 `new_customers` + `returning_customers` 兩個 list。短期：必須在 ARCHITECTURE.md 警告。

## 共通根因
6 個 bug 全部是「不同 layer 的 schema 默契錯位」：
- v1 vs v2 schema 共存（bug 1）
- 兩個並行 list 命名不一致（bug 2）
- 同一字串的 raw / canonical 兩形態（bug 3 / 4）
- JSON 欄位幻覺（bug 5）
- 欄位命名誤導（bug 6）

## 後續動作
- [x] code 加防呆 assertion + 早期警告
- [x] ARCHITECTURE.md 加 schema 章節（offers.json / cohort customers.json / promo_customers.json）
- [x] learnings.md 追加 2026-05-05 entries
- [ ] HK spring2026 + 其他 5 個 TW HM campaign 走 SOP 補 target_skus
- [ ] ladyn / lm 兩 brand regression 確認 0 fallback regression

## 與過去的關聯
跟 2026-04-28 「`returning` 在不同工具語意不同」learning 是同一個系統病：cohort 工具的客群欄位/list 命名極度誤導、過去三個月不同人撞過至少 3 次。需要 cohort-analyzer 端做 schema 重構。
