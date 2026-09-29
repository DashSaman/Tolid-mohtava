# ماتریس قابلیت‌ها (FEATURES فارسی)

وضعیت‌ها: ✅ VERIFIED_WORKING (تست‌شده) · 🟡 PARTIAL · ⛔ BLOCKED_BY_CREDENTIAL (آماده، منتظر کلید شما) · ⚪ OPTIONAL · ❌ NOT_IMPLEMENTED

| قابلیت | وضعیت | Credential؟ | ابزار/Provider |
|---|---|---|---|
| پنل فارسی RTL (۲۱ بخش) | ✅ | خیر | Python stdlib |
| صف کار ماندگار + تاریخچه + retry cap | ✅ | خیر | jobs.py |
| تبدیل گفتار فارسی (medium/CUDA، fallback CPU) | ✅ | خیر | faster-whisper |
| لایهٔ AI چند-پرووایدر + مسیریابی وظیفه | ✅ | خیر (محلی) | LM Studio/Qwen2.5-7B |
| تحقیق + بررسی HTTP واقعی منابع | ✅ | خیر | داخلی |
| راستی‌آزمایی فنی (NEEDS VERIFICATION صادق) | ✅ | خیر | LLM محلی |
| سناریوی فارسی + مارکرهای تولید | ✅ | خیر | LLM محلی |
| هوک / بسته‌های عنوان-کاور / نسخهٔ شبکه‌ها / کامنت پین | ✅ | خیر | LLM محلی |
| مقاله + سئو از transcript (با retry/validation) | ✅ | خیر | LLM محلی |
| مسیریاب ۱۷ اسکیل | ✅ | خیر | SKILL.md واقعی |
| رسانهٔ تغییرناپذیر + checksum | ✅ | خیر | media.py |
| همگام‌سازی چند-ترکه (موج+کلپ، پیش‌پردازش مشترک) | ✅ | خیر | FFmpeg+numpy |
| بهبود محافظه‌کارانهٔ صوت | ✅ | خیر | FFmpeg |
| تدوین غیرمخرب + بازگردانی + گزارش فارسی | ✅ | خیر | editing.py |
| رندر Preview/Final + Shorts 9:16 | ✅ | خیر | FFmpeg/NVENC |
| Shorts V2 (رتبه‌بندی چندزاویه‌ای + تأیید) | ✅ | خیر | intelligence |
| سئوی سایت (خزش واقعی + تاریخچه + پیشنهاد fix) | ✅ | خیر | seo_engine |
| معماری Analytics + snapshots ثابت + آداپتورها | ✅ | خیر (اجرا ⛔) | analytics.py |
| حلقهٔ یادگیری + زمان‌بندی تطبیقی | ✅ | خیر | performance records |
| بهینه‌سازی پس از انتشار (پیشنهاد با تأیید) | ✅ | خیر | analytics.py |
| برنامهٔ هفتگی با شواهد | ✅ | خیر | intelligence |
| Knowledge Base داخلی (traceable) | ✅ | خیر | knowledge.py |
| تشخیص تکرار/کنیبالیزیشن | ✅ | خیر | content_intel |
| موتور به‌روزرسانی Evergreen | ✅ | خیر | content_intel |
| ContentOptimizationEngine (SEO/AEO/GEO/AI) | ✅ | خیر | content_intel |
| Observability + کار گیرکرده (POSSIBLY_STUCK) | ✅ | خیر | jobs.py |
| امنیت (hash رمز، قفل bruteforce، CSRF/CSP سخت) | ✅ | خیر | ops.py/server |
| آرشیو My Passport (checksum + تأیید دو مرحله‌ای) | ✅ | خیر | ops.py |
| احراز هویت پنل | ✅ (فعال‌سازی با env) | ADMIN_* | ops.py |
| بوت‌استرپ/Verify/Backup/Restore/انتقال | ✅ | خیر | setup/*.ps1 |
| انتشار dry-run | ✅ | خیر | triggers.py |
| پیش‌نویس وردپرس دو سایت | ⛔ | WP_* Application Password | publishing.py |
| اعلان Telegram | ⛔ | TELEGRAM_* | notifications.py |
| انتشار YouTube/Instagram/Facebook/LinkedIn | ⛔ | OAuth هر پلتفرم | analytics ADAPTERS |
| Analytics واقعی هر پلتفرم | ⛔ | OAuth | analytics ADAPTERS |
| GA4 (بازدیدکنندگان) | ⛔ | GA4_* | integrations.py |
| Keyword Planner (حجم جست‌وجو) | ⛔ | GOOGLE_ADS_* | integrations.py |
| GSC (عملکرد جست‌وجو) | ⛔ | GSC_CREDENTIALS | analytics |
| SERP/رقیب | ⛔/⚪ | SERP_API_KEY (اختیاری) | integrations |
| تولید تصویر (Thumbnail/Carousel) | ⛔ | GOOGLE_AI_API_KEY | skills |
| Ruflo (هم‌اردازی) | ⚪ خاموش | RUFLO_ENDPOINT | integrations |
| Screaming Frog (عنکبوت حرفه‌ای) | ⚪ جایگزین داخلی | نصب+SCREAMING_FROG_PATH | integrations |
| چند-کاربره/چند-ماشینه همزمان | ❌ خارج از هدف محلی | — | — |
