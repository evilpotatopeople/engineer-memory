# dtc-dashboard-up 印不出 tunnel link — /investigate
日期：2026-08-07
Skill：/investigate
狀態：需後續追蹤（root cause 已確認、修法提案待拍板）

## 摘要（一句話）
`~/bin/dtc-dashboard-up` 用「固定 sleep 8 秒 → grep 一次」抓 trycloudflare URL、但 URL 配發延遲實測 4~7 秒且波動、超過 8 秒就抓到空字串並**靜默印出空 URL**；streamlit + tunnel 本體其實每次都有起來、「叫不出來」的觀感全來自 link 沒印出來 + 重跑又把快好的 tunnel 殺掉重排。

## 詳細內容

**症狀**：終端機跑 `dtc-dashboard-up` 一直沒有 link。zsh history 顯示連續重跑 15+ 次。

**現場證據（2026-08-07 18:3x）**：
- streamlit 8501 LISTEN、`curl localhost:8501` → HTTP 200
- cloudflared tunnel 活著、`curl https://…trycloudflare.com` → HTTP 200（服務根本沒掛）
- `/tmp/cloudflared.log`：18:32:00 送出 quick tunnel 請求、**18:32:07 才印出 URL**（7 秒）
- 腳本時序：啟動 cloudflared 後 `sleep 8` → grep。這次 18:32:08 grep、只贏 1 秒
- 丟棄式 tunnel 實測：URL 出現在第 **4 秒**（延遲波動大、8 秒 budget 貼著跑）

**Root cause（設計層級、兩層疊加）**：
1. **固定 sleep 賽跑**：URL 配發是變動延遲（4~7 秒常態、尖峰可 >8 秒）、固定等 8 秒 grep 一次、輸了就空手。
2. **輸了完全靜默**：`URL=$(grep … | head -1)` 空結果 pipeline 仍回 0、`set -e` 不會攔、腳本照樣印「📍 URL:（空白）」、沒有任何錯誤或診斷。使用者以為壞了 → 重跑 → `pkill cloudflared` 把「再 2 秒就好」的 tunnel 殺掉重新排隊 → 連續快速重跑還可能觸發 trycloudflare 端限流（429、log 已被下一輪 truncate、無法回溯證明）→「一直沒有 link」的死循環。

**排除的假設**：`~/.dtc_dashboard_pass` 存在（非 set -e 早死）；`~/bin` 在 PATH（.zshenv 有 export、非 command not found）；streamlit 啟動正常（log 乾淨、200）。

**修法提案（最小 diff、單檔 `~/bin/dtc-dashboard-up`）**：
- `sleep 8` + 單次 grep 改成 **poll loop**：每秒 grep 一次、最多等 60 秒、抓到就往下走。
- 超時就把 `/tmp/cloudflared.log` 尾段印出來 + exit 1、把真正的錯誤（如 429）攤在使用者面前、不再靜默。
- （可選）streamlit 的 `sleep 5` 同樣改成 poll 8501 端口。

**Silent-fail 家族第 5 例**：同 2026-05-05 brand_view sync、2026-05-06 cohort hook、2026-06-10 審計揪出的第 3/4 活體——「失敗不出聲、成功不確認」。這次變體是 bash 版：`grep|head` 吞 exit code + 固定 sleep 當同步機制。

## 後續動作
- [ ] 使用者拍板後改 `~/bin/dtc-dashboard-up`（poll loop + 超時報錯）
- [ ] 改完實測一次 `dtc-dashboard-up` 全流程

## 與過去的關聯
- silent-fail 家族規範（learnings.md 2026-05-06）：成功要印 ✅、失敗要印 stderr——本案 bash 腳本同樣適用
- `investigations/2026-06-25_dtc-dashboard-回購天數卡365.md`：同一個 dashboard、上一案也是「靜默丟棄不報錯」
