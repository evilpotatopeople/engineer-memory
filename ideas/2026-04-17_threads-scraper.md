# Threads 爬蟲架構 — /office-hours
日期：2026-04-17
Skill：/office-hours
Mode：Builder (scratch-own-itch)
狀態：進行中（等 Apify actor 驗證結果）

## 摘要（一句話）
為自己監控 Threads 上品牌/產品關鍵字，選擇走 Apify + Supabase 的借刀殺人架構（每月 ~$10），用 assignment 先驗證 Apify actor 品質再決定是否繼續。

## 問題陳述
想在 Threads 上監控特定品牌名/產品名（獨特單字），每天預估命中 <50 筆。希望抓下來的資料呈現在一個簡單的 Web Dashboard 裡，能查歷史、看趨勢。

## 拷問過程關鍵答案
- **Q1 / 需求現實**：「我自己想做，主管還不知道」→ 不是 intrapreneurship，是 solution in search of a problem
- **重新 framing / 真正動機**：「我自己就會用」→ scratch own itch，健康的起點
- **Q2 / 現狀**：監控關鍵字／話題（不是追特定帳號，也不是存檔）
- **Q3 / 具體性**：品牌名／產品名（獨特單字），每天 <50 筆命中
- **Q4 / 消費方式**：有一個簡單的 Web Dashboard

## 前提（已同意）
1. **沒有官方公開搜尋 API**。Meta 官方 Threads API 只給讀自己帳號貼文，關鍵字監控只能走 headless browser 或第三方爬蟲服務。
2. **Web Dashboard 對 <50 筆/天 是過度設計**。Email digest 就能解決 80% 問題，Dashboard 是之後累積趨勢資料才需要的。
3. **帳號封鎖風險是現役等級**。Threads 反爬強，必須接受「要嘛養小號、要嘛偶爾斷線」的現實。

## 三個架構方案

### Approach A：極簡殺招（Playwright + SQLite + cron + Email）
- 部署：家裡 Mac mini / Raspberry Pi / Hetzner VPS ($0-5/mo)
- 開發：一個週末
- Completeness 7/10（沒 dashboard）
- Pros：最快驗證會不會真的用、改壞了不痛
- Cons：沒 dashboard、沒 trend chart

### Approach B：正典架構（Playwright worker + Postgres + Next.js Dashboard）
- 部署：Fly.io / Railway ($10-20/mo)
- 開發：一週
- Completeness 9/10
- Pros：功能完整
- Cons：70% 工程花在 dashboard，可能做完只用 email

### Approach C：借刀殺人（Apify + Supabase）✅ 選定
- 部署：Supabase free + Apify ($10/mo 起)
- 開發：1-2 天
- Completeness 8/10（功能完整但綁第三方）
- Pros：不用處理反爬、Meta 改版不是自己的事
- Cons：月費高 10 倍、綁 vendor、actor 品質未驗證

## 推薦過：Approach A
我推薦 A，理由是「還沒證明會天天用」。但使用者選擇 C，理由是時間價值 > 月費。接受，但 assignment 綁驗證停損點。

## Approach C 具體架構

```
Apify Threads Scraper Actor (每 30 min)
  ↓ webhook
Supabase Edge Function /ingest (去重 + 篩選)
  ↓
Supabase Postgres (posts + keywords tables)
  ↓
Supabase Studio (當 dashboard 用)
```

### Schema
```sql
create table posts (
  id bigserial primary key,
  thread_id text unique not null,
  author text,
  content text,
  posted_at timestamptz,
  url text,
  matched_keywords text[],
  scraped_at timestamptz default now()
);
create index posts_posted_at_idx on posts (posted_at desc);
create index posts_kw_idx on posts using gin (matched_keywords);

create table keywords (
  id bigserial primary key,
  keyword text unique not null,
  enabled boolean default true
);
```

### 成本估算
- Apify: $5-20/月
- Supabase: free tier 足夠（500MB DB）
- **總計 ~$10/月**

## Open Questions（待驗證才能進下一步）
1. Apify Store 上有沒有品質夠的 Threads scraper actor？review 數、更新時間、社群回饋如何？
2. 實測抓一個品牌關鍵字 24 小時範圍，誤配率多少？筆數合不合理？
3. Actor output JSON 有哪些欄位？是否包含 posted_at、author、原文？
4. Apify 的排程頻率是否有免費/便宜方案支援每 30 min 跑一次？

## 停損條件
- 誤配率 > 30% → 放棄 C，改走 A
- 找不到維護中（最後更新 <3 個月）的 actor → 放棄 C，改走 A
- Actor 月費超過 $30（超過 A 方案 6 倍）→ 重新評估

## 成功標準（Builder mode）
- 2 週內完成 Approach C 端到端（試爬 → Supabase → Studio）
- 跑 4 週，每週都有實際點進 Studio 查過資料 → 代表有價值，值得升級成 custom dashboard
- 若 4 週沒點 → 關掉 Apify 省月費，承認「其實不需要」

## 後續動作
- [ ] **今晚**：到 Apify Store 搜 "threads"，看 2-3 個 actor 的 review
- [ ] **明天**：選一個 actor，用一個真實品牌關鍵字跑 24 小時試爬
- [ ] **人眼檢查**：筆數合理性、誤配率、JSON 欄位完整度
- [ ] **根據試爬結果決定**：繼續 C / 換 A / 換 actor
- [ ] 若繼續 C：建 Supabase 專案、寫 schema、寫 Edge Function ingest

## What I noticed about how you think
- **你會自我修正**。我戳破「主管還不知道」那個 framing 後，你馬上承認「我自己就會用」。這種不為面子硬凹、願意把框架換掉的反射動作，是做產品的人真正會需要的肌肉。
- **你選 C 不是偷懶，是價值判斷**。你沒選「淡忘風賊」那個妥協選項，直接跳到 C——代表你的時間觀念是「月費 < 週末」，這個前提值得記住，下次你在做別的決策時，這個 heuristic 會再出現。
- **你還沒被這個問題真正推過**。Q2 你選「監控關鍵字」但沒選「我已經在追特定帳號」——代表你沒有「每天手動滑 Threads 抓資料」的實際疼痛。這是為什麼 assignment 要綁停損點：先驗證你會真的用，再投資工程。

## 與過去的關聯
第一份 engineer-memory ideas 檔，無過去關聯。
