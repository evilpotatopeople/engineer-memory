# dtc-campaign-analytics 修復→優化→擴充執行框架 — /plan-eng-review
日期：2026-06-10
Skill：roadmap 規劃（基於同日全套件審計 reviews/code/2026-06-10_dtc-suite-audit.md）
狀態：進行中（P0 已完成並驗收 2026-06-11、下一步 P1 golden tests）

## 摘要（一句話）
六階段框架：止血（P0）→ 架網（P1）→ 通訊與出聲（P2）→ 規則統一（P3）→ 算法升級（P4）→ 價值擴充（P5）；核心邏輯是「先架網再動刀、出聲先於修對、規則只活在一個地方」，時程錨點是 618（6/11-6/18）與其復盤。

## 進度快照（2026-06-11 P2 收官時）
P0+P1+P2 全完成（兩天）：4 個止血修復、golden 三段鏈 179 值 + 機械掃描 + pre-commit、grid/pace sidecar + lineage 履歷。附帶：真 P0 一隻（promo 5 欄解包 crash）、HTML 蒸發案破案、磁碟 30GB→5.3GB。未動：P3 規則統一（7 月）、P4/P5、52 筆 pattern 債務在帳。

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

## 推進清單 v2（2026-06-11 健檢整合後、取代下方散落的未完項）

**本週（618 期間、全是加法）**
1. [x] `midflight_check.py` 事中對照 ✅ 2026-06-11（commit 22e5839）：LIVE 掃描 / refs 日曲線中位 share / 零售口徑首個落地 / 新鮮度標註；回放驗證 spring2026 全程 -5% 帶內；hm summer D1 數字明早 10:35 起可看
2. [x] P3a-2 ✅ 2026-06-11：寄倉唯一源（692 單拆解＝全為贈品 marker、policy gift_implies_warehouse=true 待 user 終確認；dcs 污染清除、hm/lm 補變體）+ rule views（v_orders_retail/v_warehouse_orders/v_orders_day/v_repurchase_true；同日拆單假回購量化 21,984 筆、各品牌 1.7-4.1%）+ bucketing 模組（三方 1,052 點一致）+ parity 8/8 一筆不差（修時差假警報：窗口對齊 DB 涵蓋日；過程中順帶劇透 hm_tw 618 D1 凌晨 $212K/101 單）。**P3a 全部完成、P3b 材料備齊（drift 清單＝切換工作清單）**
3. [x] `_sync_temp` 保留閥門 ✅ 2026-06-11（同 commit、7 天）

**復盤週（6/19-20）**：618 復盤（P0-P2 後首次實戰、舊規則跑、產出 P3b 驗收基準）

**P3b 拆 A/B 兩類（2026-06-11 user 追問後修訂）**：
- P3b-A（語義不變、618 期間可做）：[x] A1 bucketing 切換 ✅ 2026-06-11（golden 179 零漂移；「對齊」從註解升級為同一份 code）；[ ] A2 comparator sheet05 字串比對→promo sidecar、[ ] A3 report 寄倉表位置讀取→sidecar
- 事故記錄：A1 commit 時 add -A 誤蓋章 hm summer2026 skill_output ×2 的磁碟消失（消失時點未明、疑 rebuild 測試窗口）→ 即時從 git 還原（9d0ee5e）、全 brand_view 掃描無其他遺失、pre-commit 加受保護檔案刪除攔截（80f93e1）；教訓：不盲 add -A、先看 status
- P3b-B（語義改變、復盤後）：cohort configs 改吃 warehouse_keywords（hm_tw 首次有寄倉 cohort、各品牌數字按定稿口徑移動）、dashboard 舊 views 退役；618 復盤舊新雙跑＝驗收聲明

**P4 算法（小塊、可交錯插隊）**：P4-0 估算語義標註+「低中高」改名歷史類比帶+印 n_refs、P4-1 三方法並排+分歧旗標、P4-2 小格子 shrinkage（HK 解藥）、P4-3 校準表（pre vs actual、現成 6 檔）、P4-4 品類親和度維度

**P4.5 [新]**：案型工作流摩擦小修——advance 改「偵測到 skill_output 檔自動推進」；大重構等用法穩定

**P5 擴充**：座標+信心標籤（可提前插隊）、檔期透支、ROAS 欄位+Meta API、TW/HK 準實驗、增量歸因（賴 P3b）、P5-6 成敗判準納毛利與廣告成本

**P6 自動化層（2026-06-11 user 問「能更自動化嗎」、規劃佔位；前置＝P3b 單一口徑）**：檔期排程器讀 index 自動驅動生命週期（D-7 planner / 檔期中每日 midflight / D+1 復盤全跑 / 每週 parity 巡檢 / 補資料自動重跑受影響 campaign）+ 通知通道（只在偏離/告警時找人）＝例外管理模式；人保留：案型/定價/目標拍板/洞察判定/復盤解讀。估 2-3 天。捷徑：midflight 每日 cron 一行、隨時可先上

**已拍板（user 2026-06-11）**：✅ $0 政策——`total>0 AND 有客` 為全系統零售口徑；✅ 寄倉口徑——per-brand 共用表 + **gift marker 證據力 = paid_only**（贈品 marker 僅有付款訂單算寄倉證據；主標記不分金額沿用 2026-05 裁決）。Canonical 寄倉數定稿：ladyn_tw 13,820 / dcs_tw 4,231（舊廣網 8,071 之灌水拆除）等、parity 8/8 驗證
**已完成拍板**：commit baseline ✅ 2026-06-11（d5ab1e4 基建 + a9ebbd4 618 備戰既有變更、pre-commit 檢查兩輪通過）

## 後續動作
- [x] P0-1：修兩個 silent hook（planner/comparator 換 promo 合規塊）✅ 2026-06-11
- [x] P0-2：no_ref_data 反轉 + join 覆蓋率（estimate_revenue 回傳 join_coverage、main 印 ✓/⚠️）✅ 2026-06-11
- [x] P0-3：_shared/atomic_io.py 新增、7 個寫入點全換 atomic_write_json ✅ 2026-06-11
- [x] P0-4：load_config 加 _validate_plan_config（HK 沿用 TWD 桶 → SystemExit；逃生口 ALLOW_BASE_BUCKETS_FOR_HK）✅ 2026-06-11
- P0 驗收：py_compile 10 檔 / atomic 模擬中斷原檔完好 / 合成資料覆蓋率 67% + miss 格正確標記 / HK guard 正反例全過 / 4 入口 import 健康（皆 PASS、未 commit）
- [x] P1-1 golden test pilot（cohort × goldenx_tw）✅ 2026-06-11：`_shared/qa/`（make_fixture.py 確定性抽樣 / fixtures/goldenx_tw_history.csv 2191筆 / golden_check.py / golden 115 值）；隔離靠 DTC_CAMPAIGN_INDEX + DTC_SKIP_SYNC_HOOKS 兩個新環境開關 + goldenx 假品牌；驗收全過（確定性重跑 PASS / 破壞測試 DAYS_PER_MONTH 擾動→精準變紅→還原→綠）
- [x] P1-1b golden 三段鏈（cohort→promo→planner、共用 tmp index、179 鎖定值）✅ 2026-06-11；planner/promo 補 DTC_SKIP_SYNC_HOOKS guards。**上線首日抓到真 P0**：promo parse_orders 位置解包寫死 5 欄、inputs 已被同步管線重建成 10 欄 → 對正式檔案直接 crash（schema 跨時代家族）；已修成 DictReader header-aware
- [x] P1-2 audit_patterns.py（bare except / exc+pass / capture 無 rc / flat_rows 孤兒；baseline 制、52 筆既有債務在帳、只擋新增）+ run_checks.sh（~3s）+ git pre-commit hook（SKIP_CHECKS=1 可跳）✅ 2026-06-11
- [x] 順手修：refresh_master_data.py 加 .bak 保留上限 3 份（曾堆 133 檔/7.8GB）✅；既有舊檔清除待 user 確認
- [ ] P1-1c（選配）：comparator/report golden + dcs 品牌 fixture（品類規則內嵌 dcs_base、值得鎖）
- [ ] 跟 user 確認 $0 幽靈列是否已在餵入前清掉（影響 P3 view 設計）
- [x] 磁碟瘦身（user 2026-06-11 核准）：30GB→5.3GB。.git 22GB→2.2MB（17 個 tmp_pack 殘骸 + reflog expire + gc --prune=now、正史 145 commits 不動）；bak 1.4GB→178MB（gzip、refresh_master_data 改自動 gzip 備份）；剩餘組成全正當（duckdb 2G / raw_orders 1.5G / outputs+brand_view ~1G）
- [x] P2-2 pace 曲線改讀 pace_profile.json（xlsx fallback、io 來源印 console）✅ 2026-06-11：golden 全綠零更新（json/xlsx 同源 compute_pace_profile、curve 完全一致）；跨 CLI 位置解包讀取點全數消滅（grid+pace 都走 sidecar、xlsx 只剩 fallback）
- [x] 案型 HTML 蒸發 root cause（user 回報）✅ 2026-06-11：recommender 預設寫 brand_view、cohort 每跑完自動 rebuild rmtree 洗掉、白名單只保 skill_output_*.md。修：MANUAL_PRESERVE_GLOBS 擴 6 patterns（案型推薦 xlsx/html、workflow_state.json、briefings、methodology_snapshot）+ 備份 read_text→read_bytes（二進位安全）；rebuild 實測 3 檔含 binary xlsx 全存活
- [x] P2-3 lineage 審計塊 ✅ 2026-06-11：`_shared/lineage.py` 收集器；cohort/promo/planner 三個 ingest 全計帳（讀入/缺OID/日期解析失敗/重複/匿名排除/金額coerce）+ planner 折入 grid/pace io 與 join 覆蓋率；結尾印「資料履歷」塊 + planner 寫進報表 00_目錄 banner。golden 如預期只紅 00_目錄 dims 一項、其餘 178 值不動
- **P2 收官（2026-06-11）**：機器介面（grid/pace sidecar）+ 異常出聲（lineage）全落地、xlsx 只剩 fallback 角色。下一站 P3 中央廚房（7 月）、P4 小塊可隨時插隊
- [x] P3a-1 規則對賬（2026-06-11）：DB 已有半個規則層（v_customer_orders 編 total>0+有客、chuancang_orders 編寄倉、product_dim 編贈品/品類、rich_line_items 編 canonical+包數）。Parity 探針 ladyn_tw：全部/retail 數字 CSV vs DB **完全一致**（98,184 / 64,759）；寄倉規則**分家 692 單**（DB 廣網 14,343 vs cohort 策展清單 13,651、DB 的 %寄倉% 連贈品 marker 也抓）；v_order_repurchase **無 gap>0 同日拆單規則**（known lesson 未進 DB、待 P3a-2 補）；line_items.category 全空、canonical category = product_dim join
- [ ] P3a-2：rule_views_build.py（含 gap>0 回購修正）、寄倉 keyword per-brand 共用表（cohort config ↔ DB 單一源）、bucketing 共用模組、全品牌 parity harness
- [ ] P3b（618 復盤後）：CLI 逐支切 views + comparator/report xlsx re-parse 退役；復盤舊新雙跑當驗收
- [ ] P3 開工前重訪此檔、按當時現實調整

## 與過去的關聯
- 審計來源：`reviews/code/2026-06-10_dtc-suite-audit.md`（P0 各項的 file:line 都在裡面）
- P3 = 2026-05-18 拍板「共用 DuckDB、campaign-analytics 未來也查這顆（不急）」的優先級升級
- P4-3 校準迴路與 cognition_db prediction_history（Gap I）同向、可整合
- 漸進式小塊原則：feedback_incremental_collaboration（2026-05-18）
