# Investigation: dtc-pre-campaign-planner 短檔 vs 長檔 ref 業績虛高 ~3x

**日期**：2026-05-21
**Skill**：/investigate（inline、不是 formal session）
**狀態**：已結案、v2.1 ship
**Bug 類型**：設計層級錯誤（累計型 metric 跨檔期失配）、教學意義高、別場景會重現

## 摘要

planner v2.0 從 cohort 07 表讀 `recall × avg_spend` 這兩個欄位是「整檔（ref_days）累計」、套到 plan 時沒乘 `plan_days / ref_days`、長檔等量套到短檔。Lady N 618_2026（3 天）用 spring2026 + summer2025（8 天 ref）跑出 TW 中標 $1.77M、實際合理 $664K、虛高 2.95×。

## 觸發

User 跑 Lady N 618_2026 pre-planner、看到 3 天合計 $1.77M、直覺「3 天業績超高」、要求拆解。

如果 user 沒覺得不對勁、bug 會繼續存在（spec 沒寫天數對齊、過去產出的報表也沒人 challenge）。

## 投資階段

### Phase 1: 重現 + 拆數字

跑兩次 ladyn_tw_plan_618_2026 + ladyn_hk_plan_618_2026、確認數字 reproducible。

### Phase 2: Analyze — 找算法位置

```bash
grep -n "estimate_revenue\|recall\|avg_spend" analyze.py
```

定位到 `estimate_revenue()`（analyze.py:525）核心公式：
```python
cust_total += now_n * v['recall']
rev_total += now_n * v['recall'] * v['avg_spend']
```

再找 `v['recall']` / `v['avg_spend']` 怎麼算的：
```python
# read_grid_from_cohort_report:
out[(r, m, f)] = {
    'recall': in_cnt / pre_n if pre_n else 0,        # 整檔累計
    'avg_spend': in_rev_n / in_cnt if in_cnt else 0, # 整檔累計
}
```

→ 確認 recall / avg_spend 都是 **ref 整檔（不是 per-day）**、套到 plan 時沒乘 `plan_days / ref_days`。

### Phase 3: Hypothesize

線性外推 sanity check（用歷史檔期實際 GMV）：

| 活動 | 天數 | GMV | 日均 |
|---|---:|---:|---:|
| spring2025 | 14d | $2,400,040 | $171K |
| summer2025 | 8d | $1,573,690 | $197K |
| autumn2025 | 8d | $1,288,042 | $161K |
| lunar2026 | 8d | $1,854,912 | $232K |
| spring2026 | 8d | $1,901,123 | $238K |

歷史日均 ≈ $200K/d × 3 天 = **$600K**（無 618 強度加成）
v2.0 planner 估算中標 = **$1.77M**（= 每天 $590K = 歷史日均的 3 倍）
偏誤 = 2.95×

線性 normalize（× 3/8 = 0.375）後 v2.1：
- 老客：$848K × 0.375 = $318K
- 新客：$923K × 0.375 = $346K
- 合計：$664K（≈ 線性外推 $600K × 1.1）

驗證假設成立。

### Phase 4: Implement

加 `PLAN_DAYS_NORMALIZE` config knob（預設 `'linear'`）、`estimate_revenue` 接 `ref_day_scales` 參數、每個 ref per_ref 業績 × scale 再進分位池。Sheet 03 加 banner、console log 同步顯示。

## Root Cause

**累計型 metric 跨檔期套用、沒做天數對齊 check**。具體：

1. cohort 07 表的設計目標 = 「描述該活動發生了什麼」、recall / avg_spend 是「該活動期間累計」、不是「per-day intensity」
2. planner v2.0 直接讀這兩欄、套到「不同天數的 plan」、暗藏假設「ref 天數 = plan 天數」
3. spec 沒寫這個假設、code 沒檢查、user 看數字才發現

## 為什麼這個 bug 會通過：

- spec v2.0 §3.3.1 沒提到天數
- 過去都用 8 天 plan vs 8 天 ref、scale ≈ 1.0、bug 隱形
- 第一次出現 3 天短檔（618）才暴露
- 沒有自動 reality check（estimated daily vs historical daily）

## 修正

v2.1 ship：
- `PLAN_DAYS_NORMALIZE = 'linear'` 預設
- `estimate_revenue` 接 `ref_day_scales`
- Sheet 03 + console banner

詳見 SPEC.md §3.3.4、CHANGELOG.md v2.1、SESSION_LOG_2026-05-21.md。

## 為何追加到 learnings.md（符合 ≥1 條件）

- ✓ root cause 是設計層級錯誤（累計型 metric 沒區分 vs 強度型）
- ✓ 教學意義高、別場景會重現（任何 cohort 07 表的累計欄位跨檔期套用都有此風險）
- ✓ 影響範圍跨多個 brand config（不只 Lady N）

## 後續動作

- [x] Spec §3.3.4 + changelog v2.1
- [x] SESSION_LOG_2026-05-21.md
- [x] learnings.md 追加（2026-05-21 三條 v2.1 + 三條 v2.2）
- [x] cognition_db ladyn_tw.principles_validated capture
- [x] 其他 brand plan config 重跑校準（13 個全跑完、全過 reality check）
- [x] 加 INTENSITY_MULTIPLIER knob（短檔強度補正）
- [x] 加自動 reality check（estimated daily vs historical daily 差 > 50% 印警告）
- [x] 升級為 empirical normalize（v2.2、用 ref 自己的 08x 曲線當 scale）

## 同日續：v2.2 升級為 empirical normalize

User 在 v2.1 ship 後問「活動長短對召回率影響真的是線性嗎？」、跨 86 檔活動實證 Day-N 累計分布、發現 linear 兩端都偏離：
- 短 plan vs 長 ref（3d vs 8d）：linear 37.5% / 實證 42.9% → linear 輕度低估
- 長 ref 套短 plan（16d vs 8d）：linear 200% / 實證 ~100% → linear **嚴重高估**

v2.2 解法：empirical mode（讀每個 ref 自己的 08x 日累計曲線當 scale）、改成 default。Lady N TW 618 從 v2.1 $664K → v2.2 $743K（+12%）；HK 618 +37%。

詳見 SESSION_LOG_2026-05-21.md「同日續」section。

## 衍生學習（v2.2 後追加）

- **SPEC 寫「保守估、可接受」就是要驗證的地方**：v2.1 寫的 SPEC 警告變真實 bug、user 問才驗證。
- **跨檔累計 metric 預設不是 linear**：HK D1-3 ~50% / TW D1-3 ~43% / 長檔嚴重飽和、需要 per-ref 個別曲線、不能跨 brand 統一公式。
- **Default 反映設計選擇**：升級 default 不用怕短期數字 break（v2.1→v2.2 同日二度改 default、user OK 因為實證背書）。

## 與過去的關聯

- 2026-05-05 `offer_sku_segment_bug_chain.md`：同類「spec 沒寫的隱含假設、user 發現才暴露」
- 2026-05-05 `brand_view_sync_silent_fail.md`：同類「過去從沒人 challenge 的安靜失敗」
- 共通教訓：**輸出層自動 reality check 是抓這類 bug 的最後防線、不能依賴 user 直覺**
