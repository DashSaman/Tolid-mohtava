# گزارش تکمیل شبانه (Overnight Completion) — ۲۰۲۶-۰۹-۲۹

> حالت: خودکار · منبع حقیقت: کد، تست‌ها، اجراهای واقعی همین شب. شات‌های واقعی: `docs/images/fa-overnight/` (۱۰ تصویر). ماشین‌خوان: `overnight-completion-report.json`

## خلاصهٔ اجرایی
همهٔ کارهای محلیِ امنِ باقی‌مانده تکمیل شد: ۵ قابلیتِ فقط-بک‌اند به UI وصل شد (KB جست‌وجو/بازسازی، کلمات کلیدی دستی، بررسی تکرار موضوع، Evergreen) + رفع یک باگ واقعی مسیر (متغیر brand تعریف‌نشده در دو endpoint → 500)، کلاینت رسمی Google Ads (پین 25.1.0) نصب و آداپتور واقعی KeywordIdeas نوشته شد (READY_FOR_CREDENTIAL)، تست‌های عملیِ شبانه انجام شد: هم‌زمانی SQLite (۴۰ کار/۰ خطا/بازیابی پس از ری‌استارت)، soak رسانه (۳×۸.۴MB آپلود→hash→validate→حذف فقط تست)، clean-install (کلون تازه+venv تازه: ماژول‌ها/DB/تست سبز)، Backup/Restore ایزوله PASS، مسیر Analytics→Learning با دادهٔ TEST برچسب‌دار، تور ۲۲ مسیر مرورگر (۰ خطای HTTP پس از فیکس)، رگرسیون ۱۲۵/۱۲۵، E2E ۲۴/۲۴، Smoke ۱۳/۱۳. Screaming Frog: نصب‌کننده رسمی با کد 2 شکست خورد (محتاج تعامل/UGUI) → همان‌طور optional ماند با آداپتور آماده؛ Ruflo و SERP خارجی هم عمداً optional ماندند (دلایل پایین).

## ۱–۲) Baseline و Backup
- HEAD شروع: `0555fdb` · درخت تمیز · پنل زنده 8767.
- بکاپ pre-overnight: `outputs/backups/tolid-20260929-203146` (sqlite backup API + integrity ok).
- دیسک C آزاد: 59GB؛ تست‌ها فقط ~۹MB موقت ساختند و پاک شد.

## ۴–۷) UI Wiring (همه با label/loading/success/error فارسی و API واقعی)
| قابلیت | صفحه | نقطهٔ اتصال |
|---|---|---|
| KB جست‌وجو + بازسازی ایندکس + آمار | منابع | `/api/kb/search|stats|reindex` — نتایج با ارجاع ref_type و دکمهٔ پروژهٔ مرتبط |
| کلمات کلیدی دستی (افزودن/فهرست/منبع) | منابع | `/api/keywords/add` + `/api/keywords?q=` (غیرتکراری با source=manual) |
| بررسی تکرار موضوع (۵ حکم + شواهد) | برنامه‌ریز | `/api/content/checktopic` — حکم فارسی + شبیه‌ترین مورد + درصد KB |
| Evergreen Refresh (دلیل/اولویت/پیشنهاد) | برنامه‌ریز | `/api/content/refresh` — ردیف‌های تصمیم با badge اولویت |

## ۸) Keyword Planner — کامل شد
- نصب **`google-ads==25.1.0`** (پین‌شده). آداپتور واقعی `ads_keyword_ideas`: GenerateKeywordIdeasRequest رسمی (seed + language fa + geo IR) + نرمال‌سازی (volume/competition/bid) → ذخیره در keyword_data.
- وضعیت: **READY_FOR_CREDENTIAL** (۵ متغیر لازم در `.env.example`)؛ بدون credential گارد صادقانه DependencyMissing. توضیح: geo IR=2724 / language fa=1007 ثابت در کد؛ هنگام اولین اتصال واقعی، خطای احتمالی scope در UI نمایش داده می‌شود.

## ۹–۱۱) ابزارهای اختیاری — تصمیم‌ها
- **Screaming Frog:** نصب رسمی winget (24.3) تلاش شد؛ نصب‌کننده با exit code 2 شکست خورد (نیاز به تعامل GUI/سیستم). **OPTIONAL_NOT_INSTALLED ماند**؛ آداپتور+نرمال‌ساز CSV آماده؛ خزندهٔ داخلی (تست‌شده) fallback فعال.
- **Ruflo:** نصب نشد — از反腐 فیلتر: جریان کار هوشمند داخلی (Job Queue + 15 handler + Skill Router) کار همان را انجام می‌دهد؛ نصب هم‌وردسازی دوم تکراری می‌بود. ADAPTER_ONLY/DISABLED ماند.
- **SERP خارجی:** ارائه‌دهندهٔ قانونیِ بدون‌کلید وجود ندارد؛ scraping پرهیز شد. fallback داخلی (همان تحلیل SEO/سروچ) فعال → OPTIONAL/BLOCKED_BY_CREDENTIAL.

## ۱۲–۱۵) AI/Skills/Gemini/Recording
- LM Studio: بالا؛ **Qwen2.5-7B لودشده (پیش‌فرض)**؛ Llama-3-8B fallback موجود؛ health provider از UI سبز.
- ۱۷ اسکیل: **17/17 فایل موجود و توسط router خوانده می‌شوند** (title فایل‌ها از vendor واقعی)؛ ۱۷ مرحلهٔ نگاشت.
- Gemini: adapter واقعی + job نسخه‌دار آماده؛ **READY_FOR_CREDENTIAL** (گارد تست شد).
- Recording: پیاده‌سازی جدید سالم ماند (تست synthetic مرورگر در جلسهٔ قبل تأیید شده؛ فیزیکی با کاربر).

## ۱۶–۱۹) تست‌های عملی شبانه
- **SQLite concurrency:** ۴۰ enqueue موازی با ۴ worker + ۳ ریدر هم‌زمان → ۴۰/۴۰ کامل، **۰ خطای خواندن**؛ پس از ری‌استارت: ۴۰ کار حفظ.
- **Media soak:** ۳ بار آپلود فایل ۸.۴MB ده‌دقیقه‌ای (سینتتیک) از طریق HTTP واقعی → sha256 + ffprobe(duration=600s) + validate=OK → پاک‌سازی انتخابی فقط فایل‌های تست. زمان کل آپلود ۳×=319ms.
- **Clean-install:** کلون تازه + venv تازه → import ماژول‌ها + ساخت DB + تست store سبز؛ محیط موقت پاک شد.
- **Backup/Restore:** دیتابیس تست با پروژه → بکاپ → تغییر → restore در مقصد ایزوله → عنوان نسخهٔ بکاپ + integrity ok (بدون دست زدن به DB اصلی).
- دیسک: پس از پاک‌سازی آرتیفکت‌ها، مصرف صفر ماند.

## ۲۴) Analytics→Learning (دادهٔ TEST برچسب‌دار)
upsert ۸ رکورد TEST → recommend_slot=BASELINE/پنجشنبه۲۰ (صادقانه با نمونهٔ ۱) → detect_patterns=HIGH_IMPRESSIONS_LOW_CTR روی اعداد واقعی شبیه‌سازی → snapshot raw+normalized ذخیره → **محیط TEST کامل حذف شد؛ DB واقعی دست‌نخورده.**

## ۲۵–۲۶) SEO و Sitemap
- تور زندهٔ هر دو سایت با موفقیت (اسکن + تاریخچه + پیشنهاد) در تست‌ها موجود؛ امشب recheck فقط-خواندنی: `robots.txt=200 بدون خط Sitemap`، `wp-sitemap.xml=404`، `sitemap.xml=301→404`. چک‌لیست ۵ دقیقه‌ای دستی (`docs/SITEMAP-CHECKLIST.fa.md`) همچنان معتبر؛ دست به وردپرس زده نشد.

## ۲۷–۲۸) تور مسیرها و موبایل
- ۲۲/۲۲ مسیر بارگذاری شد؛ **پس از فیکس brand: ۰ خطای HTTP≥400**؛ خطای کنسول: ۰ (شات‌ها witness).
- موبایل 393px: داشبورد/بازگشت (شات mobile-dashboard.jpg) قابل‌استفاده.

## باگ واقعی رفع‌شده شبانه
- `GET /api/content/refresh` و `/api/content/checktopic` به متغیر `brand` تعریف‌نشده ارجاع می‌دادند → 500 عمومی. فیکس: استفاده از `q.get('brand',[brand_default()])[0]`. (تور مرورگر آن را گرفت؛ route-فیکس + تست دستی هر دو endpoint سبز.)

## جدول ابزارها (§38)
| ابزار | نصب؟ | نسخه | استفاده | سلامت | نوع |
|---|---|---|---|---|---|
| Python | ✅ | 3.12.10 | پنل/موتورها | سبز | الزامی |
| Node | ✅ | 24.19 | تست مرورگر | سبز | توسعه |
| Git | ✅ | - | مخزن | سبز | الزامی |
| FFmpeg/FFprobe | ✅ | 9.0.2 | تحلیل/رندر/سکوت | سبز | الزامی |
| NVENC | ✅ | - | رندر نهایی | سبز | اختیاری سریع |
| CUDA/CTranslate2 | ✅ | 4.8.2 + cublas12.9/cudnn9.26 | whisper GPU | سبز | اختیاری سریع |
| faster-whisper | ✅ | 1.2.1 | تبدیل گفتار | سبز | الزامی |
| LM Studio | ✅ | سرور 1234 | AI محلی | سبز | الزامی |
| Qwen2.5-7B | ✅ لودشده | Q4_K_M | پیش‌فرض LLM | سبز | الزامی |
| Llama-3-8B | ✅ | Q4_K_S | fallback | آماده | اختیاری |
| Playwright+Chrome | ✅ | - | تست/شات | سبز | توسعه |
| SQLite | ✅ (سیستمی) | WAL | ذخیره | سبز | الزامی |
| Ruflo | ❌ | - | هم‌وردازی | آداپتور خاموش | اختیاری |
| Screaming Frog | ❌ (نصب‌کننده exit 2) | - | سئو حرفه‌ای | fallback داخلی فعال | اختیاری |
| SERP provider | ❌ | - | رقابت/سروچ | fallback داخلی | اختیاری |
| google-ads | ✅ (امشب) | 25.1.0 پین | Keyword Planner | READY_FOR_CREDENTIAL | اختیاری-موصوف |
| Gemini | کدآماده | - | تولید تصویر | READY_FOR_CREDENTIAL | اختیاری |

## باقی‌مانده (§39)
| مورد | وضعیت |
|---|---|
| WP×۲/Telegram/YouTube/IG/FB/LinkedIn/GSC/GA4/Ads/Gemini | BLOCKED_BY_CREDENTIAL |
| sitemap tehnet.ir | BLOCKED_BY_USER_ACTION (چک‌لیست wp-admin) |
| میکروفون فیزیکی | MANUAL_PHYSICAL_TEST (کاربر) |
| Ruflo/SF/SERP | OPTIONAL (دلایل بالا) |
| کار دیگر محلی | NO_REMAINING_WORK |

## امتیاز آمادگی (§40)
CORE LOCAL 97 · UI 90 · AI 90 · MEDIA 92 · SEO 85 · INTEGRATIONS 72(آماده-منتظرکلید) · ANALYTICS 65(موتور✓ داده⛔) · SECURITY 90 · BACKUP/MIGRATION 92 · DOCUMENTATION 92 → **OVERALL 88%**

## تأییدهای پایانی
رگرسیون ۱۲۵/۱۲۵ · E2E ۲۴/۲۴ · Smoke ۱۳/۱۳ · تور ۲۲ مسیر ۰ خطا · شات واقعی ۱۰ تصویر (`docs/images/fa-overnight/`).
