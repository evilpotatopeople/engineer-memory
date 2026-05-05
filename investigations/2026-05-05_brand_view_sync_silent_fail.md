# offer_behavior 寫完沒觸發 brand_view sync — silent fail

日期：2026-05-05
Skill：手動記錄（接續 `2026-05-05_offer_sku_segment_bug_chain.md` 的 follow-up）
狀態：已結案、auto-sync hook 已加

## 摘要（一句話）
`_shared/offer_behavior.py` 改完 sheet 04 顯示邏輯、跑 `python3 _shared/offer_behavior.py --brand heromama --market TW` 重生 per-campaign xlsx 到 `dtc-promo-analyzer/outputs/`、但**沒觸發 `_shared/sync_brand_view.py update`**、user 開 `brand_view/{brand}/{market}/{campaign}/09_案型行為.xlsx` 看到的永遠是舊版、誤判「修法沒生效」。

## 任務脈絡
- 接續 SKU × 客群分析升級任務的 sheet 04「target_skus / categories」欄位顯示優化
- 我改完 code、user 截圖回報「春日野餐加料區還是顯示一個品項」
- 第一反應以為改動沒生效、查 code 看到 edit 在
- 直接讀 raw cell value、stdout 也顯示空 D 欄
- 後來才看 mtime：`brand_view/...09_案型行為.xlsx` 18:58 vs `dtc-promo-analyzer/outputs/...案型行為.xlsx` 19:02 — brand_view mirror 落後 4 分鐘

## 根因
`_shared/offer_behavior.py` 跑完寫兩個地方：
1. `brand_view/{brand}/{market}/_brand_level/案型行為庫.xlsx`（brand-level、helper 內 `shutil.copy` 同步）
2. `dtc-promo-analyzer/outputs/{Disp}_{Mkt}_{slug}_案型行為.xlsx`（per-campaign、寫完就結束）

**第二個寫入沒觸發 `sync_brand_view`**。`sync_brand_view.py` 的 watch list 認得 `*_案型行為.xlsx` 並 mirror 到 `brand_view/{brand}/{market}/{campaign}/09_案型行為.xlsx`、但只在 `promo_analyzer` 跑完才呼叫。`offer_behavior` 是獨立的 reader、沒接這個 hook。

結果：
- 改動 promo config 後重跑 `promo_analyzer` → brand_view 同步（OK）
- 只改 `offer_behavior` 邏輯後重跑 `offer_behavior` → brand_view per-campaign 永遠舊（silent）

## 修法
`offer_behavior.py:1202` 結尾加 subprocess hook：

```python
import subprocess
sync_script = REPO / '_shared' / 'sync_brand_view.py'
n_synced = 0
for camp in campaigns:
    result = subprocess.run(
        ['python3', str(sync_script), 'update', camp],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        n_synced += 1
    else:
        print(f'  ⚠️ sync_brand_view 失敗 {camp}: {result.stderr.strip()[:200]}')
if n_synced:
    print(f'  ✅ brand_view 鏡像已同步（{n_synced}/{len(campaigns)} campaign）')
```

**關鍵防呆**：
- `capture_output=True` + 失敗印 stderr、不 silent fail（解 2026-04-28 同類教訓）
- 失敗包在 try/except、不影響 promo outputs 寫入（保 graceful degradation）

## 驗證
- TW 7/7 campaign sync ok
- HK 9/9 campaign sync ok
- promo outputs 跟 brand_view 的 mtime + 檔案 size 完全一致

## 教訓
- **凡是寫下游檔案的 CLI、必須觸發所有 mirror 路徑** — 不能假設「user 重跑某個別的 CLI 會順便 sync」
- **mtime 是 silent fail 的最後防線** — 這次 root cause 是看 mtime 才發現、code review 看不到
- **新加的 hook 必須印成功訊息** — `✅ brand_view 鏡像已同步（7/7 campaign）` 讓未來人知道有跑、跑完幾個

## 與過去的關聯
- 接續 `investigations/2026-05-05_offer_sku_segment_bug_chain.md` (6 個 schema bug)
- 同類於 learnings 2026-04-28 「靜默 try/except 把 NameError 也吞掉」、但形式不同：那次是 hook 寫了但觸發失敗、這次是 hook 根本沒寫
- 廣義 silent fail 家族第 N 起、應該推動專案級的「下游 mirror sync 規範」（每個 producer 必須宣告自己 mirror 到哪些路徑、CI 驗證）
