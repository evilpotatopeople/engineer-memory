# dtc-campaign-analytics 修復→優化→擴充執行框架 — /plan-eng-review
日期：2026-06-10
Skill：roadmap 規劃（基於同日全套件審計 reviews/code/2026-06-10_dtc-suite-audit.md）
狀態：進行中（P0 已完成並驗收 2026-06-11、下一步 P1 golden tests）

## 摘要（一句話）
六階段框架：止血（P0）→ 架網（P1）→ 通訊與出聲（P2）→ 規則統一（P3）→ 算法升級（P4）→ 價值擴充（P5）；核心邏輯是「先架網再動刀、出聲先於修對、規則只活在一個地方」，時程錨點是 618（6/11-6/18）與其復盤。

## 詳細內容

### 框架總邏輯（6 條原則）
1. **先架網再動刀**——回歸測試先於一切重構，否則每次改動都在裸奔
2. **出聲先於修對**——看得見的錯比看不見的對更有價值；先讓系統會喊，再讓它更準
3. **規則只能活在一個地方**——資料清洗規則進 DuckDB views，不再散在各 CLI 與 Claude 記憶
4. **每塊小到一次對話能驗證**（user 漸進式原則）
5. **活動週只做加法、不做改寫**——618 期間不動核心計算路徑
6. **每個數字最終要能自我說明**——來歷（lineage）+ 信心（校準/樣本量）

### P0 止血包（今天～明天、618 開跑前；合計約半天）
全部是「不改變數字」的低風險修復：
1. 修 2 個 silent hook（planner:2192、comparator:1982，抄 promo:3444 合規塊）→ 解決：跑完工具後 brand_view 默默過期（silent-fail 家族第 3、4 活體）
2. `estimate_revenue:669-673` no_ref_data 條件反轉 + join 覆蓋率 print（<50% 大聲警告）→ 解決：grid join 失敗完全隱形（HK 全 0 事故機制）
3. `_shared/atomic_write_json`（temp + os.replace）替換 campaign_index + cognition_db 等 7 個寫入點 → 解決：中央狀態檔寫一半毀檔、平行跑互蓋
4. `load_config` 加 guard：MARKET=HK 且 M_BUCKETS == config_base TWD 預設 → hard fail → 解決：下一個忘記覆寫的 HK config 默默全 0
- 驗收：跑一次 618 plan config，console 出現 join 覆蓋率與 sync ✅；模擬中斷寫入 index 不毀檔

### P1 架網（618 活動週內；1-2 天）
1. Golden-output 回歸測試：每品牌一份 fixture CSV、5 個 CLI 各鎖 20-30 個關鍵數字、diff script → 解決：零測試、「user 直覺是唯一防線」
2. 兩支機械 audit：hook 四條規範掃描器、`flat_rows` 孤兒迭代器掃描器 → 解決：「修 A 漏 C」家族復發、promo 過濾一致性不可證
3. 集成成單一 `run_checks.sh`
- 驗收：故意改壞一個計算，checks 變紅

### P2 通訊與出聲（618 復盤後；2-3 天）
1. cohort 隨 xlsx 同步輸出 `grid.json` + `pace.json`；planner 改讀 JSON（xlsx 留 fallback）→ 解決：位置解包/標籤字串 re-parse 那一整族脆弱性（根因：Excel 同時當人機介面）
2. Lineage 審計塊標準化：每個 CLI 結尾固定輸出「讀 N 列 / 丟 N 列＋原因 / join 覆蓋率 / fallback 清單」、同步寫進報表 banner → 解決：異常默默跳過；把 user「跑完必審計」規矩變 code 強制
- 驗收：golden tests 全綠（介面切換前後數字 bit-for-bit 一致）

### P3 規則統一・中央廚房（7 月、雙 11 備戰前；1-2 週大塊）
1. DuckDB rule views：Total>0、贈品排除、同日拆單、canonical SKU（strip_qty）、真回購 gap>0 全部進 views → 解決：規則多副本、規則活在 Claude 記憶、忘了套就算錯
2. 分桶模組單一化：planner/cohort 共用同一個 bucketing module → 解決：標籤兩份手工對齊、join 兩端漂移
3. CLI 逐支切換查 views（一次一支、golden tests 驗證）
- 紅利：dtc-dashboard 共用同層、兩產品數字天然一致
- 驗收：同一指標 CLI vs dashboard 一致；刪掉重複規則代碼

### P4 算法升級（小塊、可與 P2/P3 交錯）
1. 三方法並排估算 + 分歧旗標（格子查表法 / 歷史日均外推法 / 同 tag 類比法並列；分歧大→提示人工判斷）→ 解決：單方法依賴；最便宜、618 後第一個做
2. 小格子 shrinkage（empirical Bayes 縮合、小樣本格子向大盤靠攏）→ 解決：HK 小樣本雜訊（3 人格子的召回率是擲骰子）
3. 校準迴路：planner 歷史準度表（pre vs actual 偏差分布；現成 6 檔可起步、每檔自動 +1）→ 解決：預估數字不自我說明
- 驗收：planner 報表出現三方法並列 + 「本工具歷史誤差 ±X%」行

### P5 價值擴充（問更好的問題；按需排）
1. 數字帶座標 + 信心標籤：關鍵指標印歷史分位（「8 檔同 tag 裡排第 6」）、結論標 ✅/🟡/⚠️ 對齊 cognition_db v/f/m/h → 便宜、可隨時插隊
2. 檔期透支視角：檔後 N 週 vs 平期 baseline、量「向未來借的業績」→ 大促淨值現形
3. 廣告花費結構化 + ROAS：spend 從手動 markdown 變 campaign-index 欄位、報表自動算（後接 Meta API、既有 roadmap）
4. TW/HK 準實驗對照 sheet（同檔期不同案型 = 天然對照；標 caveat）
5. 增量歸因：客戶自然回購節奏 baseline → 活動真實增量（vs 收割本來就會發生的需求）→ 天花板最高、**依賴 P3 的 DuckDB 層**、獨立規劃一輪

### 總表
| 階段 | 主題 | 核心解決 | 規模 | 時機/前置 |
|------|------|---------|------|----------|
| P0 | 止血 | silent hook×2、join 隱形、狀態檔毀損、HK config 陷阱 | 半天 | 立刻、618 前 |
| P1 | 架網 | 零測試、家族復發不可防 | 1-2 天 | 618 週內可做 |
| P2 | 通訊+出聲 | xlsx 雙介面、默默跳過 | 2-3 天 | 618 復盤後、需 P1 |
| P3 | 規則統一 | 規則多副本、桶定義漂移 | 1-2 週 | 7 月、需 P1 | 
| P4 | 算法 | 單方法、小樣本、無校準 | 各 0.5-1 天 | 可交錯、不需 P3 |
| P5 | 擴充 | 增量/透支/ROAS/對照 | 各 0.5-3 天 | #5 需 P3、餘可插隊 |

### 排程（2026-06-10 排定、錨點 = 618 與雙 11 備戰）
| 日期 | 內容 | 備註 |
|------|------|------|
| 6/10（今） | P0-1 hooks、P0-2 join 覆蓋率 | ~1.5h、不改數字 |
| 6/11 | P0-3 atomic write、P0-4 HK guard | 618 D1、全是加法 |
| 6/12-13 | P1-1 golden tests（ladyn_tw pilot → 4 品牌） | |
| 6/16-17 | P1-2 機械 audit ×2 + run_checks.sh | 活動尾聲 |
| 6/19-20 | 618 復盤（user 主導、全 pipeline 實戰驗證 P0/P1） | |
| 6/23-27 | P2 sidecar + lineage、P4-0 估算語義標註、P4-1 三方法並排 | |
| 6/30-7/4 | P4-2 shrinkage、P4-3 校準表、P5-1 數字帶座標 | |
| 7/7-18 | P3 DuckDB 規則層（兩週 block、一次切一支 CLI） | |
| 7/21-8/8 | P5-2 透支、P5-3 ROAS 欄位、P5-4 TW/HK 對照、P4-4 品類親和度維度 | |
| 8 月中起 | P5-5 增量歸因獨立規劃輪 | 雙 11 備戰（10 月）前完成 |

### 方法論健檢（2026-06-10、讀完 estimate_revenue + estimate_new_revenue 後的結論）
**健康的部分**：分層歷史類比估算（誠實、無虛構成長假設）；v2 修掉 independent percentile aggregation 偏誤（per-ref 一致性）；per-ref empirical day curve；MAD outlier；雙向 reality check；cognition_db 的 v/f/m/h 知識論分類。促/客群/比對三支描述型 CLI 本質是計數機、方法論無虞。

**弱點（按嚴重度）**：
1. **低/中/高 ≠ 統計信賴區間**——是 2-6 個歷史檔的樣本範圍、同 tag ×2 複製是 pseudo-replication（移動分位但不增加資訊）。掛 p25/p75 之名給了不該有的精確感。解法：改名「歷史類比帶」+ 印 n_refs（P4-0）。
2. **小格子召回率未縮合**——3 人格子的 0%/33%/67% 是雜訊（P4-2 shrinkage）。
3. **案型/機制不在模型內**——估算語義 = 「若本檔表現如同歷史同 tag 檔」；折扣深度/門檻結構的差異全在 metadata 文字層、不進數字。短期解：語義標註（P4-0）；長期：TW/HK 準實驗（P5-4）+ metadata 累積夠多後再考慮建模。
4. **Method F 新客估算與投放脫鉤**——new = old/(1-share)-old：(a) 老客估算誤差 1:1 乘法傳遞；(b) 新客數其實是投放的函數、模型看不到廣告（P5-3 補資料層）；(c) high×p75、low×p25 是情境配對、區間乘法加寬。
5. **無增量歸因**——「成效 = 檔期 GMV」混入本來就會發生的自然回購、系統性偏愛深折扣大檔（P5-5）。判準也缺毛利/廣告成本（P5-6 新增：成功定義納入 margin + ad cost）。
6. （輕微）day-curve 修總量不修組成——短檔回流偏向高忠誠格、per-cell 診斷略偏、總量無虞。stationarity 假設與 ref 入選偏差（有 cohort 報表者才成為 ref）靠 reality check 緩解、文件註明即可。

**服用結論（分用途）**：事後拆解 → P0/P1 修完即可長期服用；量級規劃（下檔多大）→ 可服用、但輸出必須當「歷史類比帶」讀而非預測、HK 樣本少要打折；因果判斷（哪個案型有效、真 ROI）→ 目前不是藥、是筆記（cognition_db），P5-4/P5-5 之前別當模型結論吃。

### 本節新增項目
- P4-0 估算語義標註 + 區間改名（排 6/23、近零成本）
- P4-4 品類親和度維度（RFM 格子內混品類客、對品類主打檔失準；中成本）
- P5-6 判準擴充：成敗定義納入毛利與廣告成本（依賴 P5-3）

### 架構判定（2026-06-11、user 問「要不要重構」）
**判決：不重構、走絞殺者演進（P1 網 → P2 介面 → P3 規則）。** 骨架五個決定是對的（CLI 算數/LLM 解讀分離、五 CLI 對應工作流、檔案資產+registry、本地零依賴、Excel 給人）。三個形變（單體 analyze.py、語意核心五拷貝、xlsx 機器介面）全用既有 roadmap 演進解。明確不做：整套重寫/換 pandas/換正式 DB——現有 code 內嵌數月踩坑的業務 edge case（寄倉雙重身份、schema 斷層、幽靈列），重寫＝全部重踩。重構觸發條件（到了再動）：品牌 >10 / 多人並行操作 / server 化。服務邏輯缺口：事中監測薄弱、校準迴路未閉合（P4-3）。

## 後續動作
- [x] P0-1：修兩個 silent hook（planner/comparator 換 promo 合規塊）✅ 2026-06-11
- [x] P0-2：no_ref_data 反轉 + join 覆蓋率（estimate_revenue 回傳 join_coverage、main 印 ✓/⚠️）✅ 2026-06-11
- [x] P0-3：_shared/atomic_io.py 新增、7 個寫入點全換 atomic_write_json ✅ 2026-06-11
- [x] P0-4：load_config 加 _validate_plan_config（HK 沿用 TWD 桶 → SystemExit；逃生口 ALLOW_BASE_BUCKETS_FOR_HK）✅ 2026-06-11
- P0 驗收：py_compile 10 檔 / atomic 模擬中斷原檔完好 / 合成資料覆蓋率 67% + miss 格正確標記 / HK guard 正反例全過 / 4 入口 import 健康（皆 PASS、未 commit）
- [x] P1-1 golden test pilot（cohort × goldenx_tw）✅ 2026-06-11：`_shared/qa/`（make_fixture.py 確定性抽樣 / fixtures/goldenx_tw_history.csv 2191筆 / golden_check.py / golden 115 值）；隔離靠 DTC_CAMPAIGN_INDEX + DTC_SKIP_SYNC_HOOKS 兩個新環境開關 + goldenx 假品牌；驗收全過（確定性重跑 PASS / 破壞測試 DAYS_PER_MONTH 擾動→精準變紅→還原→綠）
- [ ] P1-1b golden 擴到其餘 CLI（promo/planner）與其他品牌 fixture
- [ ] P1-2 機械 audit ×2（hook 合規掃描、flat_rows 孤兒掃描）+ run_checks.sh
- [ ] 跟 user 確認 $0 幽靈列是否已在餵入前清掉（影響 P3 view 設計）
- [ ] P3 開工前重訪此檔、按當時現實調整

## 與過去的關聯
- 審計來源：`reviews/code/2026-06-10_dtc-suite-audit.md`（P0 各項的 file:line 都在裡面）
- P3 = 2026-05-18 拍板「共用 DuckDB、campaign-analytics 未來也查這顆（不急）」的優先級升級
- P4-3 校準迴路與 cognition_db prediction_history（Gap I）同向、可整合
- 漸進式小塊原則：feedback_incremental_collaboration（2026-05-18）
