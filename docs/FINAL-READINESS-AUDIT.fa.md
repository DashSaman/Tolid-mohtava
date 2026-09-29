# ممیزی نهایی آمادگی محصول (REPORT ONLY — ۲۰۲۶-۰۹-۲۹)

> روش: راستی‌آزمایی مستقیم روی Git HEAD `3137e57`، نمونهٔ زندهٔ `127.0.0.1:8767`، سورس واقعی (44 GET / 35 POST route، ۱۵ job handler)، گردش مرورگر روی هر ۲۲ مسیر sidebar، و تست‌های wire-level. هیچ اصلاحی انجام نشده است. نسخهٔ ماشین‌خوان: `final-readiness-audit.json`

## ۱–۲. نمونهٔ زنده (شواهد دقیق)

| مورد | شاهد |
|---|---|
| Git HEAD | `3137e57` «ui: visual acceptance pass…» — درخت تمیز (۰ تغییر) |
| پورت/پروسه | 8767 ← pid 42784 `python` (start 17:14) از همین مخزن |
| Frontend سروشده | `index.html` دارای `atmo` (v3) · `style.css` دارای Aurora tokens |
| Database | `outputs/panel/data/content.sqlite` — ۲۳ جدول، content=0 (پنل کاربر فعلاً خالی) |
| AutoClaw روی 8766 | همچنان زنده (پروکسی قدیمی محافظت‌شده)؛ لانچر خودکار 8767 را برمی‌دارد |

## ۳. فهرست کامل قابلیت‌ها (طبقه‌بندی دقیق)

WORKING: پنل ۲۲ صفحه‌ای فارسی RTL · دفتر محتوا+تأیید نسخه‌دار · صف کار ماندگار+observability · رسانه تغییرناپذیر+checksum · whisper فارسی (medium/CUDA، fallback CPU) · تدوین غیرمخرب+restore+گزارش فارسی · sync خودکار (preprocessing+Pearson+کلپ) · بهبود صوت · رندر Preview/Final+NVENC+نسخه‌بندی · Shorts ساده+V2 · سئو خزش واقعی+تاریخچه+پیشنهاد fix · حلقهٔ یادگیری/زمان‌بندی/بهینه‌سازی (با دادهٔ واقعی) · برنامهٔ هفتگی شواهد-محور · KB traceable · کنیبالیزیشن · Evergreen · ContentOptimizationEngine · اعلان محلی · آرشیو My Passport (approval+checksum) · bootstrap/verify/backup/restore · تست‌ها (109).

PARTIAL: مرکز اتصال‌ها (کارت کامل ولی «راهنمای اتصال» مودالِ ساده و بدون OAuth flow) · تصاویر/Thumbnail (فقط آپلود+تأیید) · احراز هویت (کد کامل، پیش‌فرض خاموش، بدون UI ورود) · sync دستی (افست قابل ذخیره در DB ولی UI ذخیرهٔ دستی ندارد).

UI_ONLY / BACKEND_ONLY: ۱۱ GET + ۱۰ POST بک‌اند فاقد دکمه در UI (فهرست در §۶) — موتورها زنده‌اند ولی از پنل دست‌نیافتنی‌اند.

BLOCKED_BY_CREDENTIAL: وردپرس×۲، Telegram، YouTube/IG/FB/LinkedIn، GSC، GA4، Keyword Planner، Gemini.

OPTIONAL_NOT_INSTALLED: Ruflo، Screaming Frog، SERP provider.

NOT_IMPLEMENTED: تولید تصویر واقعی (Gemini/carousel/infographic/quote/graphic) · OAuth مرورگری · ارسال واقعی تلگرام/شبکه‌ها · multi-user.

BROKEN: — (هیچ موردی یافت نشد)

## ۴. ممیزی ۲۲ صفحهٔ sidebar

همه ۲۲ مسیر لود شدند (تور مرورگر واقعی؛ صفر خطای HTTP≥400). صفحات بدون دکمهٔ فعال در وضعیت خالی: نسخه‌های ویدیو، تصاویر، مرکز تأیید، تقویم، منابع — صحیح است چون داده ندارند (empty state دارند؛ dead نیستند). صفحات پرکاربرد: داشبورد(۷)، Analytics(۷)، کارها(۸)، اتصال‌ها(۲۲)، اسکیل‌ها(۱۷)، تنظیمات(۱۸).

## ۵. ممیزی دکمه‌به‌دکمه (خلاصهٔ یافته‌ها)

- WIRED: ۲۵ endpoint POST از UI صدا زده می‌شود (ساخت پروژه، تصمیم‌ها، آپلود، transcribe، edit_detect، رندرها، shorts v2، مقاله، سئو اسکن/پیشنهاد، social، dry-run، weekly-plan، whisper model/benchmark، providers save/health، اعلان‌ها، assets state، archive copy دکمه دارد، analytics record/proposal-decide/optimization دکمه دارد).
- **BACKEND_ONLY (UI ندارد — ۱۰ POST):** `analytics/optimize` (فقط «ثبت رکورد پایه» هست؛ دکمهٔ «اجرای بهینه‌سازی» نیست)، `analytics/snapshot`، `archive/copy` *(دکمه هست ولی فقط با Passport متصل؛ بدون دیسک: پیام صادقانه)*، `auth/login`+`logout` (UI ورود ندارد)، `ga4/fetch`، `kb/reindex`، `keywords/add`، `sync/clear`، `sync/save` (افست دستی در UI ذخیره نمی‌شود؛ فقط خواندنی).
- **BACKEND_ONLY (۱۱ GET):** `analytics/performance|snapshots`، `archive`، `content/checktopic|optimize|refresh`، `kb/search|stats`، `keywords`، `ops/observability` (+ `/api/integrations_old_never` endpoint مرده که باید حذف شود).
- DEAD_BUTTON: صفر (هر دکمهٔ رندرشده پاسخ HTTP سالم داد؛ فقط حالت‌های خالی مشروع هستند).

## ۶. ممیزی گردش کار

| مرحله | UI | بک‌اند | اتصال | نکته |
|---|---|---|---|---|
| ایده/ویس→پروژه→transcript | ✅ | ✅ | ✅ E2E | — |
| تحقیق/بررسی/سناریو/هوک | ✅ | ✅ | ✅ E2E | کیفیت JSON وابسته به مدل |
| تأیید سناریو | ✅ | ✅ | ✅ E2E | — |
| ضبط آپلود→transcribe→sync→بهبود صوت | ✅ | ✅ | ✅ E2E | sync دستیِ UI ندارند (§۵) |
| تدوین→restore→preview→FINAL(تأیید) | ✅ | ✅ | ✅ E2E | — |
| Shorts (V2→رندر) | ✅ | ✅ | ✅ E2E | — |
| تصویر/Thumbnail | 🟡 | ❌ تولید نیست | — | فقط آپلود/تأیید دستی |
| مقاله→سئو سایت→پیشنهاد fix | ✅ | ✅ | ✅ E2E | «اعمال fix» ⛔ WP credential |
| Social variants | ✅ | ✅ | ✅ | انتشار واقعی ⛔ |
| تأیید انتشار→dry-run | ✅ | ✅ | ✅ E2E | — |
| انتشار واقعی | ❌ | 🟡 آداپتور WP آماده | ⛔ | OAuth شبکه‌ها نه در UI نه بک‌اند |
| Analytics→یادگیری | 🟡 | ✅ | ⛔ | ثبت دستی واقعی کار می‌کند؛ ingestion ⛔ |

## ۷. اتصال حساب‌ها — عمق هر ۱۱ مورد

هر ۱۱ کارت: UI ✅ · آداپتور/مسیر تست ✅ · وضعیت صادقانه ✅ · بدون نمایش Secret ✅. تفاوت «آداپتور هست» با «اتصال واقعی کار می‌کند»:
- **وردپرس×۲:** `wordpress_draft` واقعی (REST) — تست فقط بعد از credential. READ: بله (اختیاری). WRITE: فقط draft. IDEMPOTENT: بله (کلید).
- **Telegram:** `telegram_send` واقعی — تست دکمه دارد.
- **YouTube/IG/FB/LinkedIn:** فقط status+health؛ **هیچ کد ingest/publish نوشته نشده** (پس از OAuth باید پیاده شود).
- **GSC:** فقط adapter declaration (بدون کد گزارش‌گیری). **GA4:** `ga4_fetch` واقعی (runReport) ولی UI ندارد. **Keyword Planner:** store+وضعیت؛ بدون کد API. **Gemini:** فقط وضعیت؛ بدون کد تولید تصویر.
- Retry: فقط در job queue. Error handling: صادقانه در همه.

## ۸. Credential UX
- همه: **PowerShell environment variable** (مودال راهنما دستور دقیق می‌دهد). UI ورود secret وجود ندارد (عمداً؛ درست). OAuth مرورگری: **موجود نیست** — برای YouTube/IG/FB/LinkedIn/GSC/GA4/Ads کاربر باید خودش توکن بسازد؛ این سخت‌ترین بخش تجربهٔ کاربر است.
-.instructions دقیق‌اند (تأیید شد در مودال و CREDENTIALS-GUIDE).

## ۹. AI
- **REAL:** LM Studio:1234 + **Qwen2.5-7B-Instruct** (پیش‌فرض)؛ Llama fallback؛ provider routing واقعی؛ ۱۵ job؛ سناریو/هوک/مقاله/شبکه‌ها/کامنت/تحقیق/بررسی همه REAL (E2E).
- SKILL Router: REAL (متن SKILL.md در پرامپت‌ها). MOCK: هیچ. BROKEN: هیچ.

## ۱۰. رسانه
REAL: آپلود جریانی+SHA256+RAW immutable · whisper GPU/CPU · sync (پیش‌پردازش مشترک) · بهبود صوت · edit decisions/restore · preview/final/NVENC/نسخه‌بندی · Shorts.
فقط-synthetic: چند-GB واقعی و پروژهٔ واقعی طولانی (تست‌ها با فیکسچر ۶–۲۴ ثانیه‌ای) — ریسک عملکرد در مقیاس واقعی تست نشده.

## ۱۱. تصویر/Thumbnail
- تولید مفهوم/پرامپت: فقط از طریق اسکیل‌ها در Codex (TEXT PROMPT ONLY).
- تولید تصویر واقعی/Gemini/کاروسل/اینفوگرافیک/کوت/گرافی‌کردن: **NOT CONNECTED / BLOCKED_BY_CREDENTIAL** (کد AI-image وجود ندارد).
- آپلود+تأیید/رد دستی: WORKING (آپلود و assets/state).

## ۱۲. سئو
- خزندهٔ داخلی REAL (تا ۱۰۰ صفحه، delay، depth) · تاریخچه append-only · تشخیص+پیشنهاد fix · ContentOptimizationEngine/کنیبالیزیشن/Evergreen REAL (کد+تست).
- «اعمال fix» روی سایت: نیست (نیاز WP credential + تصمیم شما). rescan: دستی با دکمه.
- Screaming Frog: OPTIONAL_NOT_INSTALLED (نرمال‌ساز CSV آماده). GSC/Keyword: BLOCKED.
- **sitemap tehnet.ir: همچنان 404** (بازبینی امروز)؛ چک‌لیست دستی در docs/SITEMAP-CHECKLIST.fa.md.

## ۱۳. Analytics/Learning
- همهٔ پلتفرم‌ها: NO DATA/BLOCKED_BY_CREDENTIAL (آداپتور آماده؛ ingestion واقعی نیست).
- ثبت دستی عملکرد: REAL WORKING. Learning/Adaptive/Opportunity: موتور واقعی روی داده؛ **تا وقتی دادهٔ واقعی نریزد، «یادگیری از production» ادعا نمی‌شود** (تست BASELINE→DATA_DRIVEN با دادهٔ تزریقی).

## ۱۴. برنامه‌ریز
- Weekly Planner REAL (شواهد محلی). Content Matrix: از طریق اسکیل/پرامپت. Competitor/SERP: ⛔. Keyword demand: ⛔ (manual فقط). Audience questions: ❌ (ابزار جمع‌آوری ندارد). Historical performance: REAL (وقتی ثبت شود).

## ۱۵. Ruflo/MCP/اختیاری‌ها
- Ruflo: ADAPTER_ONLY (DISABLED پیش‌فرض؛ endpoint gate). MCP Manager: به‌صورت الگوی یکپارچه در integrations.py (سرور MCP نصب نیست). Screaming Frog: OPTIONAL_NOT_INSTALLED. SERP: ADAPTER_ONLY.

## ۱۶. ذخیره‌سازی/Backup/انتقال
- SSD/درایوها REAL · My Passport: شناسایی REAL (E:\) · archive copy: approval-gated REAL (تست checksum) · delete: جداگانه (پیاده نشده عمداً).
- Backup/Restore/Bootstrap/Verify: WORKING — **ولی هرگز روی یک ماشین ویندوز واقعاً تازه تست نشده** (ریسک شناخته‌شده).
- پورت 8766 هنوز توسط AutoClaw اشغال است (لازم Admin) — پنل روی 8767 سرو می‌شود.

## ۱۷. امنیت
- CSP سخت (script-src 'self') ✓ · escape وسیع (۱۴۶ نقطه) ✓ · token gate mutation ✓ · static allowlist ✓ · PBKDF2+rate-limit (کد) ✓ · **یافتهٔ P1: وقتی ADMIN_* تنظیم شود، `AUTH.check` روی مسیرهای POST اعمال نمی‌شود** (auth فقط endpoint login دارد) — یعنی فعال‌سازی auth فعلاً محافظ واقعی request-level نیست. قبل از دسترسی از راه دور باید سیم‌کشی شود.
- OAuth state/SSRF: OAuth نیست؛ fetch URLs فقط برای منابع تحقیق (scheme-checked).

## ۱۸–۱۹. UX/رنگ‌ها (فقط گزارش)
- بنفش/آبی در اشباع بالا در Hero/primary؛ مجموع قابل‌تحمل ولی نزدیک به «گیمینگ». پیشنهاد پالت حرفه‌ای‌تر برای بعد: base `#0B0F1A`/`#111827`، surface `#151C2C`، accent اصلی `#5B8DEF` (آبی آرام)، ثانویه `#8AA3C4`، success `#3FB68B`، warning `#D9A13B`، danger `#E06C75`، info `#7AA2F7`؛ کاهش saturate گرادیان‌ها به ~۷۰٪ و کاهش glowها به حاشیه‌ها.
- RTL/فونت/تراز اعداد: سالم. Modal/فرم: کارا. «شبیه دکمه ولی وایر نشده»: pipeline nodes کلیک‌پذیرند؛ چیپ‌های status کلیک‌پذیر نیستند (باید هم نباشند).

## ۲۰. صداقت مستندات
- درست: FEATURES/DAILY-USE/UI-GUIDE با شات‌های v3 منطبق.
- **مستند‌شده ولی UI ندارد:** «افست دستی» ذخیره‌شدنی · KB search UI · کنیبالیزیشن UI · Evergreen UI · GA4 fetch دکمه · ورود auth UI · «اعمال پیشنهاد».
- **پیاده ولی مستند کم:** observability page، checktopic، keyword store.
- تصاویر: همه v3 واقعی ✓.

## ۲۱. شکاف پوشش تست‌ها (ریسک‌های تولیدی تست‌نشده)
OAuth واقعی · انتشار واقعی · ingestion واقعی · تولید تصویر · پیش‌نویس وردپرس واقعی · ارسال تلگرام واقعی · پروژهٔ ویدیویی طولانی واقعی · رسانهٔ چند-GB · مهاجرت واقعی به ماشین تازه · استرس SQLite همزمان.

## ۲۲. اولویت‌ها
- **P0 (قبل از استفادهٔ روزانه):** هیچ باگ مسدودکننده‌ای نیست. تنها: تصمیم دربارهٔ پورت 8766 (Admin kill AutoClaw) — وگرنه روی 8767 استفاده کنید. → در عمل **خالی**.
- **P1 (قبل از اتصال/انتشار واقعی):** ① اعمال AUTH.check روی مسیرهای mutation ② OAuth مرورگری برای شبکه‌ها ③ ingestion واقعی YouTube/GSC/GA4 ④ پیش‌نویس وردپرس end-to-end با credential واقعی ⑤ UI برای ورود/نمایش افست دستی sync ⑥ دکمه‌های UI برای optimize/KB/keywords/checktopic/refresh/GA4 ⑦ حذف endpoint مرده `integrations_old_never`.
- **P2 (بعد از شروع روزانه):** UI جست‌وجوی KB · صفحهٔ observability · ورود auth · صفحهٔ keyword manual-add · بهبود مقاله‌نویسی با مدل بزرگ‌تر · تست چند-GB.
- **P3:** تولید تصویر Gemini · SITEMAP-CHECKLIST اجرای شما · Screaming Frog/Ruflo · پالت رنگی پیشنهادی §۱۹.

## ۲۳. تفکیک اجباری
- **REAL SOFTWARE BUGS:** ۰ (تنها endpoint مردهٔ قدیمی `integrations_old_never` = کد مرده، نه باگ رفتاری)
- **MISSING UI WIRING:** ۱۱ مورد (بخش ۵)
- **BLOCKED BY CREDENTIALS:** ۱۱ اتصال
- **EXTERNAL MANUAL CONFIGURATION:** sitemap wp-admin · OAuth token ساخت · AutoClaw admin-kill
- **OPTIONAL TOOLS NOT INSTALLED:** ۳ (Ruflo/SF/SERP)
- **VISUAL/UX ISSUES:** اشباع بنفش/آبی؛ پیشنهاد پالت §۱۹
- **DOCUMENTATION ISSUES:** ۷ قابلیت «مستند/بک‌اند ولی بدون دکمهٔ UI» (بخش ۵)
- **UNTESTED PRODUCTION RISKS:** بخش ۲۱
