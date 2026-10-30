# 汪喵雙11 第 14／15 天計畫＝0（planner 短 ref 照 Day N 硬對）— /investigate
日期：2026-10-30
Skill：/investigate
狀態：已結案（36972a7＋4c1c6f1 上線、07／08 重產 15:45、走速盤 15:49 發布）

## 摘要（一句話）
planner 07 每日形狀把 ref 第 N 天對到本檔第 N 天，ref 最長 13 天，所以 15 天檔的最後兩天（含 11/11）計畫＝0，且 ref 收尾高峰落在錯的日子（11/3、11/9）。

## Root cause
`dtc-pre-campaign-planner/analyze.py` build_pace_forecast：`day_shares[d['day_idx']]` 只用 ref 自己的 day_idx（設計註記 Q5「Day 位置對齊」），normalize 又把 Day 1–13 撐到 100%。總量外推（EXTRAP_DAY_BASIS='min'，10/6）有處理「plan 比 ref 長」，形狀層沒有。07 表頭其實一直印「⚠️ 所有 baseline 都短於當下 15 天、後段完全無樣本」，但只是一行字，沒人看、也沒擋。

## 證據
- 9 檔 ref 每日佔比全是「首日高、中段低、最後 1–2 天衝高」。
- 舊 07（TW 中標）：11/3 294 萬（7 天檔收尾疊加）、11/9 261 萬（13 天檔的 11/11）、11/10＝0、11/11＝1。
- 留一檔回測每日 MAE：雙11 2025 1.85→1.35pt、雙11 2024 2.73→1.46pt、年中慶 2026 2.15→0.97pt。

## 修法（已上線）
- `stretch_daily_to_plan`：頭對頭、尾對尾，多的天數在中段補該 ref 中段最低日（跟 EXTRAP_DAY_BASIS='min' 同假設）。
- `reshape_pace_sheets.py`：開跑後只重產 07／08，總量從報表表頭讀回、不重建客池（analyze.py 重跑會吃開跑後訂單與新認人規則）、不動 pre_estimate；寫入前用舊形狀重建逐格比對（TW／HK 都 15 天 × 12 欄一致）；舊檔 `.bak_20261030-1545`。
- `campaign_review/build.py` ref_hour_shares：比 ref 長的天尾對尾，D14／15 小時計畫不再全 0（已用模擬驗過）。
- `_shared/qa/test_pace_stretch.py` 進 run_checks 第 16 段；golden 236 值未變。

## 影響
總額不變（TW 26,594,173、HK 4,894,862），前段計畫下修：TW 累計達成 109%→123%。11/11 新中標 286 萬（10.7%），去年 11/11 佔 16%，因 7 天檔收尾佔比較低、取中位後被稀釋，可能仍偏保守。

## 後續動作
- [x] D14／15 的 vs 過往活動：改 `spec.ref_day`（前半頭對頭、後半尾對尾、中間多的天對到前半最後一天），build.py 五處與 decompose 共用（4c1c6f1）。今日報表逐行比對只多方法說明；把快取 mtime 改成 11/10 22:30、11/11 15:30 模擬，自檢 []、對照與小時計畫都有值。11/6 起對到去年同一天，11/9 不再比去年 11/11。
- [ ] 超凝雙11 等之後的規劃自動吃新形狀；已開跑或已結案的檔不會自己變。

## 與過去的關聯
- learnings「建檔時先猜、Day 1 回填的項目要變成自檢」（同日）；project_planner_extrap_min_day（10/6）只修了總量層。
