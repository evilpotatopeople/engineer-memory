# dtc-campaign-analytics 全套件審計 — /review
日期：2026-06-10
Skill：/review（範圍為全 codebase audit、非單一 PR diff）
狀態：需後續追蹤

## 摘要（一句話）
沒有發現「正在算錯數字」的 P0；核心問題是**防護機制缺位**——silent-fail hook 家族還有 2 個活體（planner/comparator）、所有 JSON 狀態檔非 atomic 寫入、planner↔cohort grid join 無覆蓋率檢查（HK 全 0 事故的機制原封不動）、外加一個方向反掉的診斷標籤。

## 詳細內容

### P1（現實條件下會出錯的脆弱設計）

1. **silent-fail hook 家族第 3、4 個活體**
   - `dtc-pre-campaign-planner/analyze.py:2192-2203`（brand_view update hook）
   - `dtc-campaign-comparator/analyze.py:1982-1993`（brand_view rebuild hook）
   - 兩者都是 `capture_output=True` + `except Exception: pass`、無 returncode 檢查、成功不印 ✅、且註解自承「fail silent」。還在函式內重新 import os/subprocess、現場拼路徑（違反四條規範的 (a)）。後果 = 2026-05-05/06 同款事故：跑完 planner/comparator 後 brand_view 鏡像默默過期。
   - 對照組（合規範本）：promo:3444、cohort:2115、offer_behavior:1348、refresh_brand_offer_db:46 都修乾淨了。**「修 A、B、漏 C」第三次重演**——validate learnings 既有結論：這個家族只能靠機械掃描根除、不能靠記憶。

2. **全部 JSON 狀態檔非 atomic 寫入 + 無鎖**
   - `_shared/campaign_index.py:39-43`：`save_index` 直接 `write_text` 覆寫 171KB 中央 registry；`upsert_campaign` 是無鎖 read-modify-write。寫到一半掛掉 = 全套工具失明（git tracked、可救回為緩解）；兩個 CLI 平行跑 = lost update。
   - 同 pattern：`case_design/quick_capture.py:73`、`cognition_db_aggregator.py:43`、`cognition_db_curator.py:81`、`workflow_state.py:99`、`append_prediction_history.py:43`、`good_recall_tracker.py:79`。
   - 修法：`_shared` 加一個 `atomic_write_json`（temp file + `os.replace`）、全部換用。

3. **grid join 無覆蓋率防護（HK 全 0 機制仍在）**
   - join 機制 = cohort xlsx 的 (R,M,F) **標籤字串** == planner 本地 `bucket_r/m/f` 生成的標籤字串（兩份手工對齊的實作）。
   - `estimate_revenue`（planner:619-621）`k not in rg: continue` 默默跳過、無 join 覆蓋率統計；桶定義不對齊 → 交集空 → 全 0。
   - `load_config`（planner:52-58）無必要鍵驗證；`config_base.py:33` 留 TWD M_BUCKETS 可被默默繼承——下一個忘記覆寫的 HK config 照樣中招（現存 6 個 HK plan config 都有覆寫 ✅、靠人工紀律）。
   - 緩解網：v2.2 reality check（planner:2081-2087）是雙向的（太高/太低都警告、進報表 banner）——但依賴 comparison 活動有 `actual` 資料、新市場沒有就沒網。

4. **per_grid `no_ref_data` 診斷方向反了**
   - `dtc-pre-campaign-planner/analyze.py:669-673`：標 `no_ref_data` 的實際是「有 ref 資料、當下客數 0」的格子；真正危險的「當下有客、ref 無資料」格子被 `continue` 默默丟掉。本該暴露 join 失敗的唯一格子級診斷、剛好往反方向指。

5. **promo 過濾一致性無法驗證（孤兒迭代器 audit 未寫）**
   - `_skip_sku_excluded`（promo:725）只有 3 個呼叫點（743/786/1898）vs 全檔 40 個 `for r in flat_rows`。部分迭代器是訂單層級、本不該套，但 2026-04-28「3/13 不一致」教訓裡說好的 audit script 沒寫、現況靠肉眼。

6. **sync_brand_view rebuild 的 rmtree 窗口**
   - `_shared/sync_brand_view.py:484-502`：手動檔備份只存在記憶體、`rmtree`（491）到寫回之間 crash = 永久遺失；備份用 `read_text` 假設 utf-8 文字檔。修法：`os.rename(VIEW_ROOT → .old)` → 重建 → 刪 .old、零遺失窗口。

### P2（衛生 / 低影響）

7. `sync_brand_view.py:431` 跨市場關聯比對 `r.get('campaign')`——**133 筆 index record 沒有任何一筆有此欄位**、功能默默死亡（schema 默契錯位家族）。
8. `sync_brand_view.py:50-54` `BRAND_DISPLAY_REVERSE` 缺 `dcs`——comparator 舊命名 fallback 對 dcs 全標 `_UNMAPPED_`（rebuild 輸出看得到、sidecar 新檔不受影響）。
9. 位置型 schema 讀取群：`read_grid`（planner:342 `row[:11]`）、`read_pace_curve`（planner:295 位置解包）、`get_kpis_from_post_report`（sync_brand_view:339-341 `row[2]/[4]/[5]`）——上游 sheet 插一欄就默默錯位。
10. `dtc-campaign-report/analyze.py:1323-1329` `_to_float` 的 `except: return 0`——現僅用於排序 key（1454）、影響小、但是未來呼叫者的陷阱。
11. `dtc-campaign-comparator/analyze.py:782/799` 讀不到的 xlsx/列默默跳過 → 表格顯示 `-`（可見的資料缺席、可接受但要知道）。
12. cohort `returning_customers`（cohort:2024）命名未改——「含新客、靠 act_class 分」的語意陷阱還在、曾造成跨工具誤讀。
13. planner/cohort ingest 無 Total>0 過濾：$0 幽靈列計入 F 次數、活躍判定、new/ret 名單（planner:407-415 連 $0 單都把 cid 加進集合）。**待跟 user 確認**餵入 CSV 是否已預清——若沒有、ladyn 史料的寄倉幽靈列會灌水。
14. config 繼承鏈全用 `from X import *`（~100 個 config）——pyflakes 類工具被致盲、config 層 NameError 無機械防護。
15. case_design 子系統有一批寬泛 `except Exception:`（html_renderer:3540、generate_strategy_briefing:68、planner_to_goal_draft:90/104、vocabulary_audit:44/70、_lib:41、recommender:74）——未逐一深查、列為待掃。
16. planner empirical 外推（1981-1987）用「最後兩個**可用** day」增量——day 不連續或檔尾 spike 時外推偏高；`closest day` 替代（1972-1976）無提示。

### 驗證過乾淨的部分
- pyflakes 全 repo 無真 undefined name（star-import 盲區除外）
- `.env` 已 gitignore、從未進 git history、無 shell=True
- v2.2 empirical normalize 設計與實作一致（per-ref 曲線、來源標記 `linear-fallback` 可見、normalize 過程全程列印）
- reality check 雙向（太高/太低都有診斷提示）且進 Excel banner
- 現存 6 個 HK plan config 全部有覆寫 M_BUCKETS/HIGH_VALUE_M_THRESHOLD
- hook 合規矩陣：promo×2、cohort×2、report×2、offer_behavior、refresh_brand_offer_db 都符合四條規範
- `upsert_campaign` 空 list 保護（2026-05-19 修的）運作中
- campaign-index.json 有進 git（毀檔可救回）

### 未覆蓋範圍（誠實聲明）
promo 七大 sheet 的計算數學（3544 行只查過濾/hook）、cohort RFM/召回內部邏輯、report orchestration 全流程、comparator join 邏輯、html_renderer/case_design_recommender 內部、`_shared/db/product_dim_build.py`（DuckDB 層）、metorik_fetcher、onboard_brand、skills/。這些要另開一輪。

## 後續動作
- [ ] 修兩個 silent hook（planner:2192、comparator:1982）——直接抄 promo:3444 合規塊、10 分鐘
- [ ] `estimate_revenue:669-673` no_ref_data 條件反轉 + 加 join 覆蓋率 print（<50% 大聲警告）
- [ ] `_shared` 加 `atomic_write_json` helper、替換 campaign_index + cognition_db 共 7 個寫入點
- [ ] `load_config` 加驗證：MARKET=HK 且 M_BUCKETS == config_base TWD 預設 → hard fail
- [ ] 寫兩支機械 audit：hook 四條規範 grep script、flat_rows 孤兒迭代器掃描（2026-04-28 既定 TODO）
- [ ] sync_brand_view rebuild 改 rename→build→delete；`BRAND_DISPLAY_REVERSE` 補 dcs
- [ ] 跟 user 確認 $0 幽靈列是否在餵入前已清（決定 P2-13 是否升級）

## 與過去的關聯
- silent-fail 家族：2026-04-28（report hook）→ 2026-05-06（cohort hook）→ 本次 planner+comparator，「修 A B 漏 C」第三次。learnings「要機械掃描」的結論被再次驗證、但 script 一直沒寫。
- HK M_BUCKETS silent fail（feedback 記憶 2026-05）：機制 = grid 標籤 join 空交集，本次定位到 code 層、確認防護仍缺。
- 納入分析 3/13（2026-04-28）：helper 建了、audit 沒寫、一致性仍不可證。
