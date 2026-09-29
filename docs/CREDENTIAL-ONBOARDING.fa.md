# چک‌لیست اتصال Credentialها (ONBOARDING) — v1.0.0-local-ready

> بعد از تنظیم هر سرویس: پنل را یک‌بار ببندید و دوباره `Open-Panel.cmd` بزنید، سپس **تنظیمات ← اتصال حساب‌ها ← «تست اتصال»**.
> Secretها فقط از environment خوانده می‌شوند؛ هیچ‌جا ذخیره/نمایش داده نمی‌شوند. با کمترین دسترسی (least privilege) بسازید.
> ثبت متغیر: `[Environment]::SetEnvironmentVariable('NAME','value','User')` در PowerShell، سپس بازکردن پنل.

---

## ۱. وردپرس تهران نتورک (tehnet.ir)

- **لازم:** `WP_TEHNET_USER` + `WP_TEHNET_APP_PASSWORD`
- **دریافت:** tehnet.ir/wp-admin ← کاربران ← پروفایل ← بخش **Application Passwords** ← Add New (نام دلخواه) ← کد ۲۴کاراکتری را کپی کنید (فقط یک‌بار نشان داده می‌شود).
- **دسترسی:** همان کاربر کافی است (سطح Author).
- **تست:** تنظیمات ← اتصال حساب‌ها ← تست اتصال؛ تست عملیاتی: صفحهٔ **انتشار** ← «درخواست پیش‌نویس» — فقط **پیش‌نویس DRAFT** می‌سازد، هیچ پست زنده‌ای تغییر نمی‌کند.
- **موفقیت:** کارت وردپرس «متصل / Credential ثبت شده» + پیش‌نویس در فهرست نوشته‌های wp-admin (وضعیت پیش‌نویس).
- **لغو:** همان بخش Application Passwords ← Revoke.

## ۲. وردپرس MyTel (mytel.one)

- مانند بالا با `WP_MYTEL_USER` + `WP_MYTEL_APP_PASSWORD` روی mytel.one.

## ۳. Telegram (اعلان‌ها)

- **لازم:** `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- **دریافت:** توکن از **@BotFather** (‎/newbot)؛ chat id از **@userinfobot** (یک پیام به ربات بدهید تا id بگیرید).
- **دسترسی:** ربات فقط به همان چت پیام می‌دهد.
- **تست:** اعلان‌ها ← دکمهٔ **«آزمون Telegram»** (یک پیام واقعی به همان چت می‌فرستد — این تنها ارسال واقعی سیستم است).
- **موفقیت:** پیام فارسی در چت شما + وضعیت موفق در پنل.
- **لغو:** BotFather ← ‎/revoke.

## ۴. Gemini (تولید تصویر)

- **لازم:** `GOOGLE_AI_API_KEY`
- **دریافت:** aistudio.google.com ← Get API key.
- **تست:** تنظیمات ← اتصال حساب‌ها ← تست اتصال؛ تست عملیاتی: پروژه ← تب **تصاویر** ← تولید.
- **موفقیت:** کارت Gemini «متصل» و تصویر واقعی (تا قبل از کلید، تب تصاویر صادقانه BLOCKED می‌ماند).
- **لغو:** AI Studio ← حذف کلید.

## ۵. Google Search Console

- **لازم:** `GSC_CREDENTIALS` (مسیر فایل JSON اکانت سرویس)
- **دریافت:** Google Cloud Console ← Service Account + کلید JSON ← دامنه در GSC برای این اکانت verify شده باشد.
- **دسترسی:** `webmasters.readonly`
- **تست:** اتصال حساب‌ها ← تست اتصال؛ سپس Analytics ← «همگام‌سازی gsc».
- **موفقیت:** کارت GSC متصل + اولین اسنپ‌شات در Analytics.
- **لغو:** Cloud Console ← IAM ← حذف کلید/سرویس‌اکانت.

## ۶. GA4

- **لازم:** `GA4_PROPERTY_ID` + `GA4_ACCESS_TOKEN`
- **دریافت:** Google Analytics ← Admin ← Data API فعال؛ Property ID از Admin؛ توکن OAuth.
- **دسترسی:** Viewer کافی است.
- **تست/موفقیت/لغو:** مانند GSC؛ موفقیت = کارت GA4 متصل + دادهٔ واقعی در Analytics.

## ۷. YouTube

- **لازم:** `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` + `YOUTUBE_REFRESH_TOKEN` (+ `OAUTH_REDIRECT_BASE`)
- **دریافت:** Google Cloud Console ← OAuth client (نوع Desktop) ← رضایت‌نامهٔ خودتان؛ Refresh Token از جریان OAuth پنل.
- **دسترسی:** `youtube.upload` `youtube.readonly`
- **تست:** اتصال حساب‌ها ← تست اتصال؛ Analytics ← «همگام‌سازی youtube».
- **موفقیت:** کارت YouTube متصل. آپلود واقعی فقط با تأیید صریح شما در پنل اجرا می‌شود.
- **لغو:** myaccount.google.com/permissions + حذف client در Cloud Console.

## ۸. Instagram / Facebook

- **Instagram:** `INSTAGRAM_ACCESS_TOKEN` — Meta App ← Instagram Graph (توکن طولانی‌مدت) — scopeها: `instagram_basic` `instagram_content_publish`
- **Facebook:** `FACEBOOK_ACCESS_TOKEN` — Meta App ← Pages — scopeها: `pages_manage_posts` `pages_read_engagement`
- **تست:** اتصال حساب‌ها ← تست اتصال؛ Analytics ← همگام‌سازی.
- **موفقیت:** کارت مربوط «متصل» + وضعیت واقعی در Analytics.
- **لغو:** developers.facebook.com ← App ← حذف/Revoke.

## ۹. LinkedIn

- **لازم:** `LINKEDIN_ACCESS_TOKEN`
- **دریافت:** LinkedIn Developers ← اپ با OpenID/Share API.
- **دسترسی:** `w_member_social`
- **تست/موفقیت:** مانند بالا. **لغو:** LinkedIn ← Settings ← Data privacy ← Permitted services ← Remove.

## ۱۰. Google Ads (Keyword Planner)

- **لازم:** `GOOGLE_ADS_DEVELOPER_TOKEN` + `GOOGLE_ADS_CUSTOMER_ID` + `GOOGLE_ADS_CLIENT_ID` + `GOOGLE_ADS_CLIENT_SECRET` + `GOOGLE_ADS_REFRESH_TOKEN`
- **دریافت:** Google Ads ← Tools ← API Center (توسعه‌دهندهٔ تست کافی است)؛ OAuth client از Cloud Console.
- **دسترسی:** فقط خواندن (Keyword Ideas).
- **تست:** اتصال حساب‌ها ← تست اتصال؛ تست عملیاتی: برنامه‌ریز کلمات کلیدی (صفحهٔ منابع/برنامه‌ریز) — جست‌وجوی واقعی Keyword Ideas.
- **موفقیت:** کارت Google Ads «متصل» + پیشنهادهای واقعی کلیدواژه.
- **لغو:** Ads ← API Center ← لغو توکن توسعه‌دهنده.

---

## نکات مشترک

- بعد از ثبت متغیرها حتماً پنل را **بازراه‌اندازی** کنید.
- اگر کارتی INVALID گفت، نام دقیق متغیر ناقص را همان کارت نشان می‌دهد.
- `OAUTH_REDIRECT_BASE` را هماهنگ با پورت واقعی پنل بگذارید (پیش‌فرض `http://127.0.0.1:8766`؛ اگر پنل روی 8767 بالا آمده، همان).
- هیچ مقدار واقعی را در Git/گفتگو/اسکرین‌شات نگذارید.
