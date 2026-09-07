# dtc-dashboard 密碼登入要填兩次、沒提示 — /investigate
日期：2026-09-07
Skill：/investigate
狀態：需後續追蹤（root cause 已確認、修法提案待拍板）

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

## 後續動作
- [ ] `auth.py`：登入成功寫簽章 cookie（`st.context.cookies` 讀、`components.html` 寫）、重連新 session 直接放行；session_state 只當快取
- [ ] `auth.py`：`clear_on_submit=False`（送丟了不清欄位）、空密碼給 `st.warning`、`pwd.strip()`、成功顯示 `st.success` + `st.spinner` 撐到 dashboard 畫完
- [ ] `auth.py`：登入 placeholder 內注入 CSS 藏 `[data-testid="InputInstructions"]`（只影響登入頁）
- [ ] `~/.cloudflared/config.yml` 加 `protocol: http2`（Cloudflare 文件對 QUIC idle drop 的建議）、`launchctl kickstart -k gui/$(id -u)/com.dtc.cloudflared` 後觀察抖動
- [ ] 殺掉殘留 quick tunnel pid 56399
- [ ] （另案）DuckDB 共用連線並發撞擊

## 與過去的關聯
- learnings 2026-08-07「服務叫不出來先驗服務是不是真的死了」：同理——密碼比對沒壞、壞的是連線與回饋。
- silent-fail 家族第 6 例（前端丟訊息只寫 console、閘對空值不吭聲、成功只 toast）。
- 2026-08-07 investigation `dashboard-up-no-link`：同一條 tunnel 鏈、上次是印 link 的 race，這次是 tunnel 本體抖。
