# TOLID-MOHTAVA — سند مرجع اصلی پروژه (MASTER STATUS)
**تاریخ ممیزی:** 2026-10-03 · **نوع:** فقط-خواندنی · **این سند از این پس سند کنترل پروژه است.**

## A. هدف پروژه
«کارخانهٔ محتوا» محلی و اول-خصوصیتی برای دو برند **تهران نتورک** (tehnet.ir) و **MyTel** (mytel.one): تبدیل ایده/ویس فارسی → تحقیق و راستی‌آزمایی → سناریو → تأیید → ضبط/رسانه → تدوین غیرمخرب → رندر/Shorts → مقاله و سئو → بستهٔ انتشار (فقط با تأیید کاربر) — با هوش مصنوعی محلی (LM Studio) و Whisper محلی، بدون هیچ انتشار بیرونی بدون تأیید صریح.

## B. معماری فعلی (تأییدشده در این ممیزی)
- **اجرا:** Docker Compose (پروژهٔ `tolid-mohtava`) — برنج `recovery/docker-isolation`
- **سرویس‌ها:** `tolid-web` (healthy، پایتون 3.12 لینوکسی) + `tolid-tailscale` (سایدکار راه‌دور) — شبکهٔ `tolid_internal`
- **انتشار میزبان:** فقط `127.0.0.1:18767 → 8766/کانتینر` (بدون 0.0.0.0؛ پورت 8766 میزبان = AutoClaw، استفاده نشده)
- **پایداری:** bind-mount واقعی `outputs/panel/data` (دیتابیس+رسانه+renders) + volumeهای `tolid-hf-cache` و `tolid-ts-state`
- **سِکرِت:** `runtime/secrets/tolid.env` (گیت‌ایگنور) — فقط `ADMIN_USER` + `ADMIN_PASSWORD_HASH` (PBKDF2-120k) — بدون وابستگی به Registry/فایروال/پروکسی میزبان

## C. قابلیت‌های ساخته‌شده (وضعیت هر حوزه — تعریف دقیق)
| حوزه | وضعیت | شواهد |
|---|---|---|
| Core application | DONE | بوت، روتینگ ۲۲ مسیر، CRUD، تاریخچه — Docker |
| Dashboard | DONE | سفر ۴۴گامی + مرورگر واقعی روی 18767 |
| Projects | DONE | ساخت/بازگردانی/حذف امن در Docker |
| Research | DONE | در Docker (LM Studio واقعی) |
| Technical verification | DONE | job ‏completed در Docker |
| Script generation | DONE | سناریو+تأیید در سفر کاربر |
| Recording | DONE در UI (منبع سینتتیک) | تست فیزیکی میکروفون = USER_ACTION_REQUIRED |
| Media | DONE | آپلود/SHA256/ffprobe در Docker |
| Whisper | DONE | درون‌کانتینر ۱۵s (بعد از پین av==18.1.0) |
| Editing | DONE | تحلیل + حکم کاربر در Docker |
| Preview | DONE | درون‌کانتینر پس از رفع NVENC-override |
| Final render | DONE | گیت تأیید + اجرا در Docker |
| Shorts/Reels | DONE | ۵s درون‌کانتینر (رفع دیادلاک حفظ شد) |
| Thumbnail | DONE | آپلود/وضعیت در سفر کاربر |
| Article | DONE | تولید با LM Studio محلی |
| Approval | DONE | دو گیت سناریو/انتشار + گیت رندر نهایی |
| Publishing | BLOCKED_BY_CREDENTIAL | فقط dry-run پیاده شده (طراحی: بدون کلید، هیچ ارسالی) |
| Calendar | DONE | صفحهٔ موعدها |
| Analytics | BLOCKED_BY_CREDENTIAL | وضعیت صادقانه؛ ورود دستی فعال |
| SEO | DONE (داخلی) | اسکن/پیشنهاد؛ GSC/GA4 = BLOCKED_BY_CREDENTIAL |
| Knowledge Base | DONE | جست‌وجو/ایندکس در Docker |
| 17 Skills | DONE | نصب/تشخیص/بستهٔ دستور |
| Jobs | DONE | صف/پیشرفت/Retry/Cancel/گیت در Docker |
| Storage | DONE | صفحهٔ منابع |
| Health | DONE | ۱۱ آیتم سبز/صادقانه |
| Notifications | BLOCKED_BY_CREDENTIAL | Telegram فقط با توکن |
| Settings | DONE | پروایدرها/اتصال‌ها |
| Authentication | DONE | mاتریس مرورگر واقعی ۷/۷ روی Docker |
| CSRF/session | DONE | بازیابی stale-gate + نشست ۱۲ساعته |
| Backup | DONE | اسکریپت host روی bind-mount معتبر است |
| Restore | DONE | آزمون ایزوله قبلی |
| Docker persistence | DONE | restart/stop/start/web-restart |
| LM Studio | DONE | host.docker.internal → ۳ مدل |
| GPU | CPU_FALLBACK | بدون دست‌زدن به درایور؛ رندر libx264 |
| Tailscale remote | **PARTIAL** | سایدکار در tailnet متفاوت (بخش K) |

## D. تغییرات مهم انجام‌شده (تاریخ مختصر)
پنل محلی → صف کار/رسانه/تدوین/رندر → UI v4 «اتاق فرمان سیگنال» → فریز v1.0.0 → اسپرینت سخت‌فزارسازی (idempotency اتمیک، ریشهٔ دیادلاک Shorts=stderr pipe) + پذیرش ۴۴/۴۴ → `v1.1.0-ui-rc1` → دسترسی راه‌دور (Tailscale نصب/فایروال فعال/اعتبارنامه) → `v1.2.0-docker-rc1` (ایزولاسیون Docker) → رفع incident ورود مرورگر واقعی (توکن CSRF + clobber نشست) → رفع منوی ⋯ بریده.

## E. باگ‌های پیدا و رفع‌شده (مهم‌ترین)
1. Shorts: نبود فایل خروجی در cmd + `-nostdin` + **ریشهٔ اصلی: پرشدن pipe(stderr) توسط آمار libx264** → stderr→فایل + watchdog + clamp (کامیت‌های 513346f/ae3b04e/9567a2d)
2. بازگردانی آرشیو مرده → «نمایش آرشیو»
3. idempotency هم‌کلید race → UNIQUE index (اثبات ۴۸ نخ)
4. ورود مرورگر واقعی: نبود هدر CSRF در login + clobber توکن نشست در boot() (8ffab32)
5. منوی ⋯ بریده: overflow:.rows + flip هوشمند + باگ specificity (5facb3f)
6. مسیر brands/ و بایند کانتینر (`TEHNET_PANEL_BIND`)

## F. وضعیت Docker
موتور 29.8.1 · هر دو کانتینر up (web healthy) · شبکه tolid_internal · انتشار فقط loopback · بدون privileged/socket/host-network · non-root (uid 10001) · HEALTHCHECK فعال.

## G. AI/Media
LM Studio ✓ (۳ مدل از طریق host.docker.internal) · Whisper ✓ ‏(CPU، ۱۵s روی ۲۴s فارسی) · FFmpeg ‏7.1.5 ✓ · GPU = CPU_FALLBACK (runtime موجود، image بدون CUDA libs — بدون تغییر درایور).

## H. UI
v4 (تیره، RTL، فارسی) — ۲۷+ اسکرین‌شات واقعی · incidentهای ورود و منو رفع و در مرورگر واقعی پذیرفته شد.

## I. SEO/Analytics
سئوی داخلی ✓ (اسکن/چک‌لیست/پیشنهاد) · GSC/GA4 ingestion پیاده‌شده ولی BLOCKED_BY_CREDENTIAL · زمان‌بندی BASELINE (بدون دادهٔ ساختگی).

## J. Integrations
**۰/۱۱ متصل** — همه `READY_FOR_CREDENTIAL` (وردپرس×۲، تلگرام، یوتیوب، اینستا، فیس‌بوک، لینکدین، GSC، GA4، Ads، جیمی‌نای). هیچ «متصل» ادعا نمی‌شود.

## K. Remote
- سایدکار: `tolid-remote` ‏(100.118.10.107) — **tailnet: golamirreza1995@**
- میزبان/گوشی: `amirreza-pc` ‏(100.87.126.12) — **tailnet: rastehnews@**
- **یک tailnet نیستند** → URL راه‌دور (`http://100.118.10.107:8766`) از دستگاه‌های شما باز نمی‌شود.
- تست‌های راه‌دور کامل‌شده: ۱۳/۱۳ قبلاً روی fallback IP میزبان (معماری قدیمی) · روی سایدکار: مسیر شبکه تأیید (socat→tolid-web) ولی لاگین کاربر pending.
- راه‌حل: ورود یک‌بارهٔ سایدکار با rastehnews@ (پاک‌کردن state volume + login URL) — P1.

## L. Security
فایروال Domain/Private/Public روشن · قاعدهٔ Tolid حذف شد · Registry ADMIN پاک شد · بدون Funnel/تانل/پورت‌فوروارد · AutoClaw مستقل (PID تغییر کرده توسط خودش: 34108→10760؛ پورت/شنونده ثابت).

## M. Tests
- **روی Docker فعلی:** سفر عملکردی کامل (upload→whisper→edit→preview→final→short→LM) ✓ · auth مرورگر واقعی ۷/۷ ✓ · S7.1 auth ۷/۷ ✓ · ماندگاری restart/stop/start ✓ · health/route ✓
- **روی host (قدیمی/مرجع):** 127/127 unit (شاخه) · 24/24 E2E · 13/13 smoke · 44/44 journey (نسخهٔ 18767-binds نه — host-native قبلی)
- **شکاف:** E2E و smoke هنوز عیناً علیه 18767 اجرا نشده‌اند (بخش N/M).

## N. مشکلات فعلی
1. سایدکار در tailnet اشتباه → راه‌دور غیرقابل استفاده (P1)
2. خواندن SQLite از میزبان حین اجرای کانتینر باعث قفل oplock و قطعی موقت 500 شد (در همین ممیزی رخ داد؛ با restart وب برگشت) — قاعدهٔ عملیاتی: هنگام اجرای استک، از میزبان به DB متصل نشوید (بکاپ فقط با stop) — P2
3. main از شاخهٔ docker جدا افتاده (+revert بیرونی 79af4b7) — نیاز به reconcile — P2

## O. باقی‌مانده
Sitemap tehnet.ir (wp-admin) · میکروفون فیزیکی · ورود سایدکار با rastehnews@ · اجرای E2E/Smoke علیه 18767 · merge شاخه به main پس از بازبینی · ۱۱ Credential.

## P. اختیاری
Ruflo · Screaming Frog · SERP خارجی (پنل بدون آن‌ها کامل است).

## Q. مسیر Release
`v1.2.0-docker-rc1` → (پس از P1/merge) → `v1.2.0-docker` نهایی.

## R. Rollback
`git checkout v1.1.0-ui-rc1` + `docker compose stop` (در worktree) + `Open-Panel.cmd` (بومی) — داده‌ها همان فایل‌های bind-mount هستند و دست‌نخورده می‌مانند.
