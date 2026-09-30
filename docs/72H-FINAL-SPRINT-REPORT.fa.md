# گزارش نهایی اسپرینت ۷۲ ساعته — v1.1.0-ui-rc1 (۱۴۰۵/۰۷/۸ · 2026-09-30)

## وضعیت: کامل

از «اپ ادمین آماده» به «سوئیت عملیات تولید محتوای AI» تبدیل شد — با حفظ ۱۰۰٪ عملکرد، دو ریشه‌یابی باگ واقعی، و هویت بصری اختصاصی.

## شناسه‌ها

- **START HEAD:** `5899c9f` (تگ v1.0.0-local-ready حفظ‌شده) · **FINAL HEAD:** `d323e59` · **RELEASE:** `v1.1.0-ui-rc1` · **PUSH:** SUCCESS
- **BACKUP:** `tolid-20260930-161212` (پیش از اسپرینت) + `tolid-20260930-175852` (release، checksum در docs/RELEASE-CHECKSUMS.txt)
- بکاپ‌های تست: بدون RAW (ایندکس رسانه).

## RELIABILITY

- **KNOWN UX/STATE BUGS FIXED:** ۳ — فهرست‌ها F5 نمی‌خواهند (refresh مسیر)؛ enqueue دوبارهٔ دکمهٔ تبدیل گفتار (binding تکراری حذف)؛ idempotency هم‌کلید اتمیک (UNIQUE + IntegrityError).
- **DUPLICATE JOB PROTECTION:** **PASS** — hammer ۴۸-نخه‌ای هم‌کلید = دقیقاً ۱ job؛ بدون job تکراری/گم‌شده/قفل SQLite در بار هم‌زمان.
- **REAL USER WORKFLOW:** **44/44** (سفر کلیکی کامل روی UI v4: ضبط سینتتیک، تحقیق، سناریو، تأییدها، آپلود، Whisper واقعی، تدوین + حکم، Preview، FINAL گیت‌دار، Shorts، مقاله LLM محلی، سئو، dry-run، Analytics صادقانه، آرشیو→بازگردانی→حذف امن، thumbnail، تأیید فنی LLM).
- **LARGE MEDIA:** size **1.01GB** · duration **۳۰ دقیقه (720p)** · result **PASS** — آپلود استریم 2.1s، sha256 ✓، ffprobe ✓، ثبت DB ✓، Whisper ۲۷s با VAD (۲۵ قطعهٔ فارسی)، کشتن پنل حین job → خطای صادقانهٔ بازراه‌اندازی → retry موفق، رندر preview کامل، Short از منبع 1GB در 28s، حذف فقط-تست ✓.
- **CONCURRENCY:** **PASS** — ۱۹ job هم‌زمان/متوالی در ۸ نخ؛ cancel و retry درست؛ بدون قفل/تکرار/گم‌شدگی.
- **FAILURE INJECTION:** **9/9** — LLM 401/403/429/500/timeout (mock server)، LM Studio قطع، رسانهٔ خراب (رندر و whisper-guard) — همه خطای فارسی صادقانه، بدون کرش.
- **SECURITY:** **PASS** — path traversal (404)، نام فایل مخرب sanitize (تأیید 0.1s)، XSS فقط دادهٔ JSON، CSRF 403، Origin متفاوت 403، آپلود بزرگ 400، OAuth state تک‌مصرف، ریس حذف موازی = دقیقاً یک حذف.
- **BACKUP/RESTORE:** **PASS** — روی دادهٔ واقعی کاربر؛ integrity ok؛ محتوا یکسان.
- **DATA VOLUME:** **PASS** — ۱۰۰ پروژهٔ تست: لیست‌ها 4-35ms، جست‌وجو پاسخ‌گو؛ دادهٔ تست پاک شد.

## باگ‌های واقعی ریشه‌یابی‌شده (مهم‌ترین دستاورد اسپرینت)

1. **Shorts از پایه مرده بود** — سه لایه: (الف) فایل خروجی به دستور FFmpeg اضافه نمی‌شد؛ (ب) نبود `-nostdin`؛ (ج) **ریشهٔ اصلی:** libx264 آمار را به stderr می‌ریزد و pipe خوانده‌نشدهٔ ۶۴KB وسط انکود پر می‌شود → دیداک‌لاک (تست‌های isolated آن را نمی‌گرفتند چون communicate هر دو pipe را می‌خواند؛ render.py سالم بود چون NVENC ساکت است). رفع: stderr→فایل موقت + watchdog + اعتبارسنجی ffprobe + clamp پنجرهٔ کاندیدا به EOF. نتیجه: از «همیشه شکست/هنگ» به **رندر ۴ ثانیه‌ای، 4/4+44/44 سبز**.
2. **بازگردانی آرشیو مرده بود** (v1.0.0) — رفع با «نمایش آرشیو».

## VISUAL DESIGN

- **DESIGN DIRECTION:** «اتاق فرمان سیگنال» — استودیوی عملیات تولید محتوای AI، تیره‌اول، ink-navy، سطوح لایه‌ای solid، شیشه فقط در topbar/دیالوگ/منو.
- **WHAT MAKES IT UNIQUE:** دو موتیف مالک محصول — نوار سیگنال موجی (صدای کاربر) زیر عنوان بخش‌ها/مونوگرام/empty-state متحرک + کانال‌های جریان خط‌چین که فقط روی نود فعالِ خط تولید جریان دارند. بدون آیکون مغز AI، بدون گرادیان بنفش، بدون قالب بازار.
- **PRIMARY PALETTE:** پایه `#080B12/#0D111B/#111827` · سطح `#151A26/#1A2130` · azure `#4E8CFF` · teal `#35B8C0` · کهربایی نادر `#E2A54B` · ok/warn/danger `#3FBF83/#E2A54B/#F07070`.
- **GRAPHICAL LANGUAGE:** شبکهٔ مهندسی کم‌رنگ + یک جاروب نوری کند؛ اعداد mono با tabular-nums؛ badge با خط وضعیت راست.
- **DASHBOARD/PROJECT/RECORDING/EDITING/APPROVAL/SEO/ANALYTICS/INTEGRATIONS/JOBS-HEALTH:** همه **PASS** (پنل «نیازمند توجه شما»، CTA آخرین پروژه، چیپ‌های صادقانهٔ AI/GPU؛ ادیتور: تمایز بصری پیشنهاد AI/حکم کاربر با خط وضعیت؛ تأییدها: کنش خطرناک متمایز).
- **RTL:** **PASS** (dir=rtl در تور، اعداد/کد LTR) · **MOBILE:** **PASS** (393px: kpi فشرده، سایدبار آیکونی، usablity تأیید در smoke/journey).
- **SCREENSHOTS:** ۲۲ عدد واقعی در `docs/images/fa-v4/` (+ ۲۷ کپچر پذیرش خام در work/shots-v4).
- **VISUAL REVISION PASSES:** **1/2** (پررنگ‌سازی موتیف سیگنال، تمایز kpi، فشرده‌سازی موبایل).

## PERFORMANCE

- **BEFORE (v3):** بدون ابزار دقیق ثبت‌شده؛ CSS شیشه/blur سنگین‌تر (516 خط، blur سراسری + ۳ بلاب انیمیت).
- **AFTER (v4):** first-load interactive **461ms** · DCL **55ms** · ناوبری 46-314ms · بازکردن پروژه **76ms** · **JS heap 4MB** · CSS سبک‌تر بدون blur سراسری.
- **REGRESSION:** **NONE** — بهبود (حذف انیمیشن‌های GPU-سنگین).

## FINAL TESTS

- **AUTOMATED:** 125/125 · **E2E:** 24/24 · **SMOKE:** 13/13 · **USER JOURNEY:** 44/44 · **ROUTES:** 20/20 · **CONSOLE ERRORS:** 0
- **REAL SOFTWARE BUGS REMAINING:** 0

## EXTERNAL

- **READY_FOR_CREDENTIAL:** ۱۱ سرویس (وردپرس×۲، Telegram، YouTube، Instagram، Facebook، LinkedIn، GSC، GA4، Google Ads، Gemini)
- **USER ACTION REQUIRED:** sitemap tehnet.ir (wp-admin) · **PHYSICAL MIC:** USER_ACTION_REQUIRED (منبع سینتتیک فقط)
- **OPTIONAL LEFT:** Ruflo · Screaming Frog · External SERP

## FINAL STATUS

- **LOCAL PRODUCT:** READY · **LOCAL DEVELOPMENT:** FROZEN · **OVERALL READINESS:** 97٪
- **ROLLBACK RELEASE:** v1.0.0-local-ready (حفظ‌شده) · **NEW RELEASE:** v1.1.0-ui-rc1
- **NEXT USER STEP:** Connect real credentials and create the first real production content.
