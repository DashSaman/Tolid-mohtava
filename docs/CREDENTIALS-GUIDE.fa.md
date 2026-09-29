# راهنمای اتصال حساب‌ها (Credential) — نام، محل دریافت، دسترسی، تست و لغو

> قواعد امنیتی: هیچ مقدار Secret در Git/دیتابیس/لاگ ذخیره یا نمایش داده نمی‌شود — فقط نام متغیر محیطی ثبت است. هر سرویس را با **کمترین دسترسی** وصل کنید. برای تنظیم: PowerShell ← `[Environment]::SetEnvironmentVariable('NAME','value','User')` سپس پنل را یک‌بار بازراه‌اندازی کنید. تست هر سرویس: **تنظیمات ← اتصال حساب‌ها ← دکمهٔ «تست اتصال»**.

| # | سرویس | نام متغیر | محل دریافت | حداقل دسترسی/scope | نحوهٔ تست در پنل | نحوهٔ لغو (Revoke) |
|---|---|---|---|---|---|---|
| ۱ | وردپرس tehnet.ir | `WP_TEHNET_USER` + `WP_TEHNET_APP_PASSWORD` | wp-admin ← کاربران ← پروفایل ← **Application Passwords** | فقط همان کاربر (سطح Author کافی است) | صفحهٔ انتشار ← «درخواست پیش‌نویس» (فقط پیش‌نویس می‌سازد) | همان صفحه ← دکمهٔ **Revoke** کنار هر Application Password |
| ۲ | وردپرس mytel.one | `WP_MYTEL_USER` + `WP_MYTEL_APP_PASSWORD` | همان مسیر روی mytel.one | همان بالا | همان بالا | همان بالا |
| ۳ | Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | توکن از **@BotFather** (/newbot)؛ chat id از **@userinfobot** | Bot (ارسال پیام به همان چت) | اعلان‌ها ← «آزمون Telegram» | در BotFather: `/revoke` |
| ۴ | YouTube | `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` + `YOUTUBE_REFRESH_TOKEN` | Google Cloud Console ← OAuth client (Desktop) + رضایت خودتان | `youtube.upload` `youtube.readonly` | Analytics ← «همگام‌سازی youtube» + وضعیت در انتشار | https://myaccount.google.com/permissions ← حذف دسترسی + حذف client در Cloud Console |
| ۵ | Instagram | `INSTAGRAM_ACCESS_TOKEN` | Meta App ← Instagram Graph (توکن طولانی) | `instagram_basic` `instagram_content_publish` | Analytics ← همگام‌سازی instagram | developers.facebook.com ← App ← حذف/Revoke توکن |
| ۶ | Facebook | `FACEBOOK_ACCESS_TOKEN` | Meta App ← Pages | `pages_manage_posts` `pages_read_engagement` | Analytics ← همگام‌سازی facebook | همان بالا |
| ۷ | LinkedIn | `LINKEDIN_ACCESS_TOKEN` | LinkedIn Developers ← اپ عضویت | `w_member_social` | Analytics ← همگام‌سازی linkedin | LinkedIn ← Settings ← Data privacy ← Permitted services ← Remove |
| ۸ | Google Search Console | `GSC_CREDENTIALS` (مسیر فایل service account) | Google Cloud ← service account + کلید JSON؛ دامنه در GSC verify شده باشد | `webmasters.readonly` | Analytics ← همگام‌سازی gsc | Cloud Console ← IAM ← حذف کلید/سرویس‌اکانت |
| ۹ | GA4 | `GA4_PROPERTY_ID` + `GA4_ACCESS_TOKEN` | Google Analytics ← Admin ← Data API فعال؛ توکن OAuth | Viewer کافی است | integrations ← تست اتصال | myaccount.google.com/permissions |
| ۱۰ | Google Ads (Keyword Planner) | `GOOGLE_ADS_DEVELOPER_TOKEN` + `GOOGLE_ADS_CUSTOMER_ID` + `GOOGLE_ADS_CLIENT_ID` + `GOOGLE_ADS_CLIENT_SECRET` + `GOOGLE_ADS_REFRESH_TOKEN` | Google Ads ← API Center (تست‌اکانت کافی) | readonly (keyword ideas) | integrations ← تست اتصال | Ads ← API Center ← لغو توکن توسعه‌دهنده |
| ۱۱ | Gemini (تولید تصویر) | `GOOGLE_AI_API_KEY` | **aistudio.google.com** ← Get API key | همان کلید (بدون صورتحساب اضافه در tier رایگان) | پروژه ← تب تصاویر ← تولید | AI Studio ← حذف کلید |

برای سرویس‌های OAuth (YouTube، Google Ads) متغیر `OAUTH_REDIRECT_BASE` هم لازم است (پیش‌فرض `http://127.0.0.1:8766`؛ اگر پنل روی 8767 بود همان را بگذارید).

**اختیاری‌ها (غیرمسدودکننده):** `SERP_API_KEY`، `SCREAMING_FROG_PATH`، `RUFLO_ENDPOINT` — پنل بدون هر سه کامل است.

بعد از تنظیم هر متغیر: پنل را بازراه‌اندازی کنید ← تنظیمات ← اتصال حساب‌ها ← وضعیت باید «متصل» شود ← یک‌بار «تست اتصال» بزنید. اگر INVALID دیدید، همان کارت دقیقاً می‌گوید کدام متغیر ناقص/غلط است.
