# Engineer Memory INDEX

> 每次 gstack skill 寫入新檔時在最上方插一行。由 skill 自動維護。

| Date | Type | Topic | File |
|------|------|-------|------|
| 2026-06-10 | plan | dtc-suite 修復→優化→擴充六階段 roadmap（P0 止血 / P1 架網 / P2 通訊出聲 / P3 規則統一 / P4 算法 / P5 擴充） | plans/eng/2026-06-10_dtc-suite-roadmap.md |
| 2026-06-10 | review | dtc-campaign-analytics 全套件審計 — silent-fail hook 第3、4活體 / JSON 非 atomic / grid join 無覆蓋率檢查 / no_ref_data 診斷反向 | reviews/code/2026-06-10_dtc-suite-audit.md |
| 2026-05-21 | learning | dtc-pre-campaign-planner v2.2 — SPEC 寫「保守估」不算完工要驗證 / 跨檔累計 metric 多是 sub-linear / Default 反映設計選擇不是 fallback | learnings.md |
| 2026-05-21 | investigation | dtc-pre-campaign-planner 短檔 vs 長檔 ref 業績虛高 ~3x — 累計型 metric 跨檔期失配（v2.1 加 PLAN_DAYS_NORMALIZE） | investigations/2026-05-21_planner-days-mismatch.md |
| 2026-05-21 | learning | dtc-pre-campaign-planner v2.1 — 累計型 metric 跨檔期失配 / broken backward compat 是對的 / user 直覺 sanity check 是 last line of defense | learnings.md |
| 2026-05-06 | learning | Schema 跨時代演進、修 keyword 要按時段掃 line items（ladyn 寄倉 2024-08 換新版 fingerprint）；line item 雙重身份（贈品 vs 訂單 marker） | learnings.md |
| 2026-05-06 | learning | 「silent try/except 吞 NameError」家族第 2 起 — cohort_analyzer sync hook 同 2026-04-28 一字不差、教訓沒記住、4 條規範化 | learnings.md |
| 2026-05-05 | learning | self-errata：給 user 解釋計算邏輯前必須驗證、不能憑 spec comment 推論（HERO 314 vs 505 解釋錯誤） | learnings.md |
| 2026-05-05 | investigation | DTC offer_behavior 寫完沒觸發 brand_view sync silent fail（user 看到舊 mirror、誤判修法沒生效） | investigations/2026-05-05_brand_view_sync_silent_fail.md |
| 2026-05-05 | learning | DTC brand_view sync silent fail — 寫下游 xlsx 不等於 sync 完成、必須觸發所有 mirror 路徑 | learnings.md |
| 2026-05-05 | investigation | DTC offer SKU × 客群分析升級 6 連 bug（schema 默契錯位 / 命名說謊 / canonical 不一致） | investigations/2026-05-05_offer_sku_segment_bug_chain.md |
| 2026-05-05 | learning | DTC SKU × 客群升級 — 6 條工程教訓（schema 命名說謊 / JSON key 幻覺 / canonical 一致性 / v1→v2 遷移完整性） | learnings.md |
| 2026-04-28 | learning | DTC suite spring2026 debug — 4 條工程教訓（silent fail / schema mismatch / filter inconsistency / 跨工具命名歧義） | learnings.md |
| 2026-04-17 | idea | Threads 爬蟲架構（選 Apify+Supabase，pending actor 驗證） | ideas/2026-04-17_threads-scraper.md |
