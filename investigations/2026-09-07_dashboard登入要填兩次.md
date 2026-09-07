# dtc-dashboard 密碼登入要填兩次、沒提示 — /investigate
日期：2026-09-07
Skill：/investigate
狀態：已結案（2026-09-07 23:50 修法落地、測試機＋正式機驗過；尚未 commit）

## 摘要（一句話）
密碼比對沒壞：WebSocket 穿 Cloudflare tunnel 今天斷了 13 次、Streamlit 重連時 server 還沒發現舊 socket 死就判「already connected」開新 session（上游 issue #8901）→ `authed` 歸零被踢回登入頁；在死掉的連線上送出登入表單會被前端**靜默丟掉還順手清空欄位**，登入閘對「空密碼送出」也不給任何訊息——三層都不吭聲，user 只看到「填對了也沒進去、再填一次就好」。

## 詳細內容

**症狀**：密碼正確（複製貼上）偶爾登不進、要填第二次；填對填錯都沒提示；「Press Enter to submit form」提示壓到密碼欄的眼睛圖示。

**現場證據（2026-09-07 23:0x）**：
- `/tmp/streamlit.log`（server 12:06 起）：13 次 `Session with id … is already connected! Connecting to a new session.`
  → 12:34、15:11、16:05、16:30、16:39、16:58、17:25、17:43、17:58、19:09、21:04、21:36、22:18。每一次＝瀏覽器重連被判新 session、session_state 歸零。
- `~/Library/Logs/dtc-cloudflared.log`（UTC）：QUIC `timeout: no recent network activity` / `Connection terminated` 叢集 ~120 行：04:19–04:37Z 連續抖動、08:41、08:59、10:00–10:14、11:37–11:39、11:56、12:14、12:29、12:32、13:18、13:38、13:58、14:49、14:53Z。
  對表（本地時間）：13 次 Streamlit 事件有 5 次跟 tunnel 斷線對得上（12:34、16:39、16:58、17:58、21:36），其餘 8 次 tunnel 沒動、是瀏覽器⇄Cloudflare 那段自己斷（睡眠／切網路／手機切背景）。
- Streamlit 1.50 + Tornado 6.5.5：server 預設 websocket ping 30s / timeout 30s（`server.py:_get_websocket_ping_interval_and_timeout`）→ server 最慢 60 秒才發現連線死；瀏覽器幾秒內就重連 → `websocket_session_manager.py:78` 判 already connected → 新 session。上游已知：streamlit/streamlit#8901「Reconnect to existing sessions instead of creating new upon unclean websocket close」。
- 前端 `index.6xX1278W.js`：`sendMessage(){ isConnected() ? send : LOG.error("Cannot send message when server is disconnected") }`——斷線時送出只印 console、畫面零回饋；`submitForm(){ … sendUpdateWidgetsMessage(); … clearOnSubmit && formCleared.emit() }`——不管有沒有送達都清欄位。
- `auth.py:52` `if ok and pwd and pwd != required` 故意跳過空值 → 空密碼送出（含「被清空後再按 Enter」）什麼都不畫、連前一次的錯誤訊息也消失；成功路徑只有 `st.toast` 3 秒 + 空白畫面等 app.py 跑 DuckDB。
- 內建瀏覽器實測（公開網址、連線正常）：錯密碼點「登入」→ 紅字「密碼錯」有畫出來（1:1 看得到）；空密碼送出 → 完全沒訊息；開著 11 分鐘、閒置 8 分鐘 → 零重連、零 console error（30s server ping 撐得住 Cloudflare Free 100s idle 限制）→ 斷線是事件驅動、不是純閒置。
- 「Press Enter to submit form」＝Streamlit 表單內 text_input 的內建提示（`InputInstructions` chunk、絕對定位在輸入框右緣），密碼欄的眼睛圖示也在右緣 → 重疊是上游版面問題、不是 theme.py 造成。
- 排除項：密碼檔 17 bytes 含結尾換行、`$(cat)` 已去掉、瀏覽器貼上也會丟換行 → 複製路徑乾淨；Enter 真實鍵盤會觸發 keypress（前端聽 onKeyPress）、內建瀏覽器工具的 key 動作不產生 keypress 才送不出、非 bug。
- 附帶發現：殘留的 quick tunnel（pid 56399、10:41 起 `cloudflared tunnel --url http://localhost:8501`）還活著、:8501 同時掛在一個隨機 trycloudflare 網址上；DuckDB `closed pending query result` 14:18–14:22 連續 10 次（`@st.cache_resource` 共用連線被並發 fragment 撞）是另一題。

**Root cause（設計層級、四層疊加）**：
1. 連線層：QUIC tunnel 抖 + 瀏覽器端斷線（一天 13 次）。
2. Streamlit 層：重連判 already connected 開新 session（#8901）→ 登入態只存 session_state、必歸零。
3. 登入閘：死連線送出＝靜默丟棄 + 欄位清空；空密碼送出無回饋；成功只 toast 3 秒。
4. 版面：內建 Enter 提示壓到眼睛圖示。

## 修法（同日落地）
- [x] `auth.py`：登入成功寫簽章 cookie `dtc_auth`＝`{到期 epoch}.{HMAC-SHA256(key=密碼, msg=v1:到期)}`、30 天；新 session 第一個 run 用 `st.context.cookies` 驗過就放行、剩 <15 天順手續期；改密碼＝全部失效
- [x] `auth.py`：`clear_on_submit=False`、`pwd.strip()`、四分支訊息：空→warning「請輸入密碼」／錯→error（欄位保留）／對→placeholder 換「🔓 登入成功，dashboard 載入中…」同 run 接著畫／cookie 放行→不畫表單
- [x] `auth.py`：登入 placeholder 內注入 `[data-testid="InputInstructions"]{display:none}`、登入後一起清掉
- [x] `~/.cloudflared/config.yml` 加 `protocol: http2`（備份 `config.yml.bak-2026-09-07`）、kickstart 後 4 條連線全 http2、precheck 也建議 http2
- [x] 殺掉殘留 quick tunnel pid 56399
- [x] `tests/test_auth_token.py` 5 條（roundtrip／過期／換密碼／竄改與壞格式／token 形狀）
- [x] 2026-09-08 追修：成功訊息「登入成功，dashboard 載入中…」原本靠下一輪 rerun 消失，但 dashboard 分頁全包 `@st.fragment`、互動只重跑分頁、外層元素永遠留著（user 回報「登入後一直顯示載入中」）。改成純 CSS：4.5 秒淡出、外層 stElementContainer 用 `:has()` 在 4.6 秒 display:none、不靠 rerun。測試機驗證：容器 display none／高 0（面板隱藏時 CSS 動畫不跑、用 Web Animations API finish() 快轉驗的）；正式機熱載入無 exception。
- [ ] （另案）DuckDB 共用連線並發撞擊（14:18–14:22 十次 closed pending query result）
- [ ] commit（user 還沒說要）

**驗證**：本機測試機 :8599（假密碼 testpass123）——空送出 warning ✓、錯密碼 error＋欄位保留 ✓、對密碼成功訊息＋dashboard＋cookie ✓、重新載入（＝新 session）不用再登入 ✓、剩 10 天的 cookie 進站續成 30 天 ✓、手機寬度（側欄收合）登入與續期都 ✓；正式機熱載入新版、空送出 warning ✓、無 exception。

**修法過程踩到的坑**：cookie 寫入元件（`components.html` 0 高 iframe）第一版塞在 `st.sidebar`——
視窗窄（手機／面板縮小）時 Streamlit 側欄整個不掛進 DOM、iframe 不載入、cookie 寫不進去（實測 R-main 有、R-side 沒有）。
改放主畫面才在所有寬度都成立。**任何靠「畫出來才執行」的東西（iframe script、components）都不能放側欄。**

## 與過去的關聯
- learnings 2026-08-07「服務叫不出來先驗服務是不是真的死了」：同理——密碼比對沒壞、壞的是連線與回饋。
- silent-fail 家族第 6 例（前端丟訊息只寫 console、閘對空值不吭聲、成功只 toast）。
- 2026-08-07 investigation `dashboard-up-no-link`：同一條 tunnel 鏈、上次是印 link 的 race，這次是 tunnel 本體抖。
