# dtc-dashboard 回購觀察天數卡死 365 — /investigate
日期：2026-06-25
Skill：/investigate
狀態：已結案

## 摘要（一句話）
dtc-dashboard 回購率 dashboard 的「回購觀察天數」被硬寫上限 365、超過就靜默丟掉那條線；放寬到 5 年(1825)、收斂成單一常數 `MAX_OBS_WINDOW_DAYS`。

## 詳細內容
**症狀**：使用者在「月度趨勢」tab 把回購天數填 > 365、按套用後那條線完全不出現、也不報錯。

**根因**：整個 codebase 裡「365」只出現在回購觀察天數的上限、且散在 `app.py` 四處：
- 回購天數 1 number_input `max_value=365`（spinner 夾回、根本打不進）
- 觀察天數（單窗版 Tab4/6）同樣 `max_value=365`
- 回購天數 2/3 即時預覽 `0 < int(_s) <= 365`
- 回購天數 2/3 真正 commit `0 < int(s) <= 365`（超過靜默丟棄）

日期區間（起始/結束）**沒有**任何 365 限制 — 所以「超過 365 跑不出來」指的是回購天數、不是日期區間。

技術上完全沒必要卡 365：SQL 用 `LEAST(w, days_since)`、window 多大都安全、days_since 自然夾住有效觀察期。365 是當初隨手設的。

**修法**：新增 module 常數 `MAX_OBS_WINDOW_DAYS = 1825`（5 年、覆蓋約 4.4 年品牌史）、四處統一引用。深層成因是「同一上限散 4 處會各改各的飄移」、用單一常數根治。

**證據**：
- py_compile 通過、grep 確認無殘留 365 上限、常數引用 4 處。
- 資料層證明（ladyn/tw, 65,594 筆 eligible）：rate_365d=35.9% / 540d=37.8% / 730d=38.5% / 1095d=38.9%、單調上升 — 多出的 ~2-3pt 長週期回購正是原本被上限吃掉的訊號。
- ⚠️ 未做 live UI click-through（需 DTC_DASHBOARD_PASS + 瀏覽器）；改動為 deterministic 的數值上限、靜態 + 資料層驗證已足。

## 後續動作
- [ ] (可選) 值 > 上限時改成 inline warning、不要靜默丟棄 — 目前 1825 在 4.4 年品牌上實質碰不到、優先度低
- [ ] (可選) 同類「散落硬上限 / magic number」掃一遍 dtc-suite 其他 CLI

## 與過去的關聯
- 同屬「silent fail」家族：2026-06-10 dtc-suite 審計也抓到 silent-fail hook（`reviews/code/2026-06-10_dtc-suite-audit.md`）。這套件反覆出現「失敗不出聲」的 pattern、值得當作系統性 review 維度。
