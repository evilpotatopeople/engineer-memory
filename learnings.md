# Engineer Learnings

> 累積的工程決策教訓。由 /retro 和 /learn 追加。按時間倒序排列，最新的在最上面。
> 格式：日期 — 情境 — 學到什麼 — 下次怎麼改

---

## 2026-08-07 / investigate — dtc-dashboard-up 印不出 link（silent-fail 家族 bash 版）

- **「sleep N 秒再 grep 一次」不是同步機制、是賽跑** — dtc-dashboard-up 固定 `sleep 8` 後 grep cloudflared log 抓 trycloudflare URL、實測配發延遲 4~7 秒波動、>8 秒就空手。凡是等外部服務就緒、一律 poll loop（每秒查、上限 30-60 秒）、不要賭固定秒數。
- **bash 的 `VAR=$(grep …|head -1)` 空結果照樣 exit 0、set -e 攔不到** — grep 沒中會被 pipeline 尾端 head 洗成 0、腳本繼續跑、印出空 URL 沒人知道失敗。關鍵變數取完要 `[ -z "$VAR" ]` 檢查 + 印 log 尾段報錯。silent-fail 家族第 5 例、python hook 的規範（成功印 ✅ / 失敗印 stderr）bash 腳本同樣適用。
- **「服務叫不出來」先驗服務是不是真的死了** — 這次 streamlit + tunnel 全程活著（curl 200）、死的只是「印 link」那一步；使用者以為掛了重跑、pkill 又把快好的 tunnel 殺掉重排、越急越叫不出來。查「起不來」類 bug 第一步：ps + lsof + curl 分清「沒起來」vs「起來了但沒告訴你」。

## 2026-08-06 / investigate — API 訂單數 vs 報表口徑差 6 萬

- **Raw API 總數 ≠ 報表口徑、對不上先找口徑不是先判「對方錯」** — 同事 Claude 用 Metorik API 抓 HM TW 得 206,235、交接文件 146,537、就下結論「API 唯一權威、文件不可靠」。實測拆解：−14,731 取消/退款/待付款 −10,190 非 TW 出貨（混站期） −12,871 bacs/cheque −20,467 ToB 寄倉批發（881 帳號、最大單一帳號 14,746 筆＝全庫 7%） → 148,311、剛好是交接數＋快照後成長。兩個數字都對。下次：兩來源數字對不上、第一步是列出雙方口徑定義（status/國家/付款/role/金額）逐維度收斂、拍板口徑就寫在自家 `METORIK_SYNC_SPEC.md`。
- **單維度驗證不能下全稱結論；「分解加總＝總數」是套套邏輯** — 同事只驗 status 一個維度（且用「各 status 加總＝總數」這種必然成立的檢查）就宣告「沒有規則可以找」；「兩 store 比值不同（71% vs 91%）→ 非系統性」也不成立——同一規則、不同市場結構（TW 寄倉批發多、HK 幾乎沒有）比值本來就不同。下次：驗「有沒有隱藏 filter」要拿候選 filter 逐一套用看能不能收斂到目標數、而不是驗 API 自己的內部一致性。
- **Metorik /orders filter 三個坑** — pagination 無 total（要 binary search page 數）；`role` filter 在 orders 端無效（eq/neq 都回 0）；`customer_id in [...]` 超過 ~20 個值**靜默回空**不報錯。跨 store 打 API 前先做「已知子集」sanity test。

## 2026-06-25 / dtc-dashboard — 回購天數硬上限 365 散在 4 處 + 靜默丟棄

- **同一個「限制值」散在多處硬寫、必然飄移成 bug** — dtc-dashboard 回購觀察天數上限 365 分別寫在 `app.py` 4 個地方（2 個 number_input `max_value`、2 個 text 驗證 `<= 365`）。使用者要看 > 1 年長週期回購、值被靜默丟掉、線不出現也不報錯。下次：任何「上限 / 門檻 / magic number」一出現第 2 次就抽成 module 常數（這次抽成 `MAX_OBS_WINDOW_DAYS`）、不要 copy-paste 數字。
- **「靜默丟棄不合法輸入」是 UX bug、不是防呆** — text_input 填 540 被 `<= 365` 默默濾掉、沒有任何提示。使用者只會覺得「壞了」。下次：驗證失敗要嘛 inline warning、要嘛根本別讓使用者填（用有 max 的 widget）、不要中間態靜默吞掉。
- **驗 threshold 類 bug 先全 codebase grep 那個數字** — 「超過 365 跑不出來」、grep `365` 全專案只有回購天數那 4 處、立刻排除「日期區間」嫌疑、根因 5 分鐘定位。下次遇到「超過某數就壞」的回報、第一步就 grep 那個數字、有沒有別處出現決定了範圍。

## 2026-05-21 / dtc-pre-campaign-planner — linear normalize 兩端都偏離、改 empirical（同日二度升級）

- **SPEC 寫「可能」「大概」「預期」的部分就是要驗證的地方、不該停在「保守估、可接受」帶過去** — v2.1 ship linear normalize 時、SPEC §3.3.4 寫「實際 recall 可能 sub-linear、所以 linear 是保守估、可接受」、沒實際驗證。User 看到 618 報表後問「活動長短對召回率影響真的是線性嗎？」我才跑跨 86 檔 Day-N 累計分布實證、發現 linear 兩端都偏離：短 plan vs 長 ref（3d vs 8d）linear 預測 37.5% / 實證 42.9%（輕度低估）、長 ref 套短 plan（16d vs 8d）linear 預測 200% / 實證 ~100%（嚴重高估）。Spec 警告變真實 bug。下次：1) 寫 SPEC 假設條款時、把「未驗證點」明確標 `🟡 unverified` 或類似 marker、定期回頭跑實證；2) 「保守估」不能當完工狀態、要驗證「保守多少」、必要時用實證數字當 default；3) 同一個 spec section 寫完警告 + 跑實證 + 用實證結果改 default、應該是同一次 PR 而不是兩次 ship。
- **跨檔期累計型 metric 的真實 scaling 通常 sub-linear、要從每個 ref 自己的曲線抽** — Day-N 累計分布跨 brand 差異不小：HK 客戶 D1-3 累計 ~50%（比 TW 高）、HK 16d ref D8 累計 53.7%（飽和很快）、TW 14d ref D8 累計 53.4%（也飽和）。**「跨 brand 一個統一公式」不對、要 per-ref 用該 ref 自己的曲線**。實作上、cohort 08x 表的 `每日新舊客趨勢` sheet 已經有所有歷史活動 daily 數據、可以即時讀。下次：1) 任何「歷史套到當下」的算法、要看「歷史那個指標可能是什麼曲線形狀」（線性 / sublinear / 飽和 / S-curve）、不該預設線性；2) 同類 spec 寫 normalize 公式前、要先跑跨檔實證確認曲線形狀；3) Per-ref 個別曲線 vs 跨 ref 統一曲線、優先用個別曲線（資料粒度更細）。
- **「Default 是行為 spec、不是 fallback」** — v2.1 ship 時把 linear 設 default、v2.2 改 empirical default。兩次都是當前最好選擇變、default 跟著變。Default 反映「設計者目前認為哪個是對的」、不是 fallback。下次升級 default 不用怕 breaking change（短期看數字會變、但這是修正過去不夠好的選擇）、只要 SPEC + CHANGELOG 寫清楚、provide 舊行為的選項（'linear' / 'none'）讓有特殊需求的人能切回去。

---

## 2026-05-21 / dtc-pre-campaign-planner — 短檔 vs 長檔 ref 業績虛高 ~3x

- **planner 從 ref cohort 07 表讀的 `recall × avg_spend` 是「整檔（ref_days）累計」、套到 plan 沒乘 plan_days/ref_days、長檔等量套到短檔** — Lady N 618_2026（3 天短檔）references = summer2025 / spring2026（都是 8 天）、planner v2.0 算出 TW 中標 $1.77M、HK 中標 HKD 155K。User 直覺「3 天業績超高」要 sanity check、線性外推（歷史日均 $200K × 3 天）= $600K、偏誤 2.95×。Root cause：ref grid 的 recall（in_cnt / pre_n）和 avg_spend（in_rev / in_cnt）兩個都是 ref 整個活動期間（8 天）的總計、planner 在 estimate_revenue 裡 `cust_total += now_n * v['recall']` 直接套到 plan 池、等同假設「短檔強度 = 長檔等量」。下次：1) 凡是用 cohort 07 表的累計型欄位（recall / avg_spend / in_rev）跨「不同檔期天數」場景、**一律先想 plan_days vs ref_days 失配**；2) 累計型 metric vs 強度型 metric（per-day）要明確分開、變數命名 `recall_total` vs `recall_per_day` 不要混；3) cohort/promo 表新增任何「跨檔期套用」邏輯前、必加「天數對齊 check」。
- **預設 normalize 為 'linear'、不為 'none'（broken backward compat 是對的）** — 修這個 bug 時面臨選擇：default 沿用舊行為（'none'）讓老 config 重跑數字不變、還是改 default 為 'linear' 讓修正成為預設？選後者。理由：1) 沿用舊行為 = 沒人會啟用修正、未來新 config 又踩坑；2) 含長檔 ref 的舊 config 重跑數字會變、但這是修正過去過估、不是 regression；3) 要等量套有明確需求、設 `'none'` 就好、不該當預設。下次遇到「修了個算法 bug 要不要 broken backward compat」、要區分「行為 bug fix」vs「介面 break」、行為 bug fix 應該破壞性更新、別讓向後相容性 trap user 繼續用錯邏輯。
- **User 直覺 sanity check 是抓 algorithm bug 的 last line of defense** — 這個 bug 在 spec 寫得很清楚（v2.0 spec §3.3.1 確實沒提到天數）、driver 也寫過好幾個 plan config、報表也產出過正常數字、沒人發現。要不是 user 看到「3 天 $1.77M」覺得「直覺太高」要求拆解、bug 會一直存在。下次：1) 在跑出「跟過去歷史 magnitude 差異很大」的數字時、自己先做 sanity check（線性外推 vs planner 估算、差距 > 50% 就主動 flag）、不要等 user 發現；2) 算法輸出加自動 reality check（例：planner 業績估算 vs 歷史日均 × plan_days、差距 > 50% 印警告）。

---

## 2026-05-06 / Schema 跨時代演進、修 keyword 要按時段掃 line items

- **商業邏輯改了、SKU 命名跟著變、舊 keyword 失效但沒人發現** — ladyn 2024-07 以前寄倉是獨立 SKU 購買行為（line item 含「寄倉服務」）、2024-08 起店家把寄倉變成後端流程、line item 只剩主品 + 「寄倉好禮 - {贈品}」訂單 marker。我修 keyword 只看了 history CSV 全期 unique line items 排序前 50、抓到 1941 訂單就以為夠（涵蓋 2021-12~2024-07）、沒**按時段切片掃 line items 模式**、沒抓到 2024-08+ 還有 4797 寄倉訂單用新版 fingerprint。User 看 cohort 報表「寄倉只到 2024-07」才發現。下次：1) 修 fingerprint keyword 時、grep 結果**必須按 month 分組**看「每月命中數隨時間是否穩定」、突然歸 0 就是 schema 變更；2) 商業邏輯演進在 codebase 完全看不到、需要 user 先講或自己挖 line items 變化；3) v1 修法以為 1941 夠、實際是冰山一角、修 keyword 只能用「掃全期不會掉訂單」當完成標準。
- **「寄倉好禮」keyword 跨「贈品 vs 真寄倉訂單 marker」雙重身份** — line item「寄倉好禮 - 沙發窩」本質是贈品 SKU、但**該 line item 出現在訂單 = 該訂單是寄倉訂單**。所以「寄倉好禮」既是贈品 marker、也是寄倉訂單 marker。對品類分類（line-item level）應歸贈品、但對寄倉客 cohort（order level）應算寄倉。修法：把「寄倉好禮」放進「寄倉」cat、不放進「寄倉-贈品」cat、順序排在贈品之前先抓走、cohort 命中正確（該客有該訂單 = 寄倉客）、營收計算稍微把「寄倉好禮」的 0 元贈品列為寄倉品類（無實質影響）。下次：1) line item 的「分類學意義」(贈品 / 主品) vs「業務意義」(訂單 marker / 客戶行為標記) 可能分歧、要看 cohort 設計目的選哪個；2) cohort_analyzer 端可以考慮加新 cohort 類型「`order_flag`」(訂單級 marker)、跟現有「`category`」(品類級) 並列、讓未來類似情況有更乾淨設計。

---

## 2026-05-06 / 「靜默 try/except 吞 NameError」家族第二起 — cohort_analyzer sync hook

詳細：根因跟 2026-04-28 「靜默 try/except 把 NameError 也吞掉」**一字不差**。教訓沒記住。

- **同一個 silent fail 模式撞了第二次：try/except: pass + capture_output=True + 沒 import 的 module + NameError 全部吞掉** — `dtc-cohort-analyzer/analyze.py` 的 brand_view sync hook 用 `os.path.*` 但 module 沒 import os、`except Exception: pass` + `capture_output=True` 把 NameError 跟 stderr 全部吞掉。所有 user 跑 cohort_analyzer 都看到舊 brand_view mirror、不知道 hook 失效。Root cause 是 cohort 修 ladyn 寄倉 cohort（18→1485 客）後、user 開 brand_view 還看 19 客誤以為「修法沒生效」、實際是 mirror 沒同步。下次：1) 凡是用既有 Path import 不要再現場 `os.path` 拼路徑（教訓寫過、又犯）；2) hook 結尾**必須印 ✅ 成功訊息**、有 silent fail 看得到（教訓寫過、又犯）；3) 不要包 `Exception`、要包具名 exception 或印 stderr 不要 pass（教訓寫過、又犯）。**4) (新)：每次發現 silent fail 應該檢查同 codebase 還有沒有其他 hook 用同一個反 pattern**—我之前修了 promo_analyzer + offer_behavior 兩個 hook、沒掃 cohort_analyzer 也有同類 hook、漏修。
- **silent fail 家族規範化**（推動專案級規範）：所有 producer 寫 outputs 後若有 sync hook、必須符合 4 條：(a) 用既有 Path 變數不現場拼 path、(b) capture_output=True 必須處理 returncode + 印 stderr、(c) 成功必須印 ✅ 訊息、(d) try/except 包具名 exception 或最少印 e。每加新 hook 跑 grep 確認其他 hook 也合規。

---

## 2026-05-05 / 給 user 解釋計算邏輯前必須驗證、不能憑記憶（self-errata）

- **憑 spec comment 推論計算邏輯、誤導 user** — user 問「sheet 02 HERO 314 vs 乾糧-貓 505 的 191 差距怎來」、我看到 promo_analyzer.py 有「2026-04-29 spec #22 區分引流品 vs 主力品」comment、就回答「HERO 排除同單有引流品的 191 訂單」。實際上 #22 comment 指的是 sheet 02_分類總覽 而不是 HERO 件數階梯、HERO 真實邏輯是 `ex_buckets = {'試吃(30g)'}`、訂單只有試吃包才不算（191 訂單只有試吃、被排除）。同單有引流品的訂單（139 個）HERO 完全有算。下次：1) 給 user 解釋計算邏輯前、必須跑 simulation 驗證（python script reproduce 真實數字）、不能只看 comment 推論；2) 看到 spec comment 不確定 scope 時、先 grep 該 spec 在哪些函式被引用、再決定是不是這個 sheet 的邏輯；3) 用「我猜」「我估」這類詞時就是要驗證的訊號、不要寫進 user-facing 解釋；4) 這跟 2026-04-28 的 schema 命名說謊家族同類—都是「憑名字/comment 推論而沒看實際 code」。

---

## 2026-05-05 / DTC suite — brand_view mirror sync silent fail

詳細：`investigations/2026-05-05_brand_view_sync_silent_fail.md`

- **寫下游 xlsx 不等於 sync 完成、user 永遠看到舊 mirror** — `_shared/offer_behavior.py` 改完 sheet 04 顯示邏輯、跑完寫到 `dtc-promo-analyzer/outputs/`、但 `brand_view/{brand}/{market}/{campaign}/09_案型行為.xlsx` 是 `sync_brand_view.py` 透過 watch list 鏡像來的、`offer_behavior` 沒觸發 sync hook、user 開 brand_view 永遠舊版、誤以為「修法沒生效」。 root cause 是看 mtime 才發現（promo outputs 19:02 / brand_view 18:58）、code review 看不到。下次：1) 凡是寫下游檔案的 CLI、必須在結尾觸發所有 mirror 路徑（subprocess 跑 sync_brand_view update）；2) hook 失敗印 stderr、不 silent；3) hook 成功印「同步 N/M campaign」、確認跑了；4) 廣義「silent fail 家族」應該推動專案級規範—每個 producer 宣告 mirror 路徑、CI 驗證 mtime 不落後。

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
