# MASTER BACKLOG — Tolid-Mohtava (فقط کار باز؛ بدون آرزو)
منبع واقعیت: `docs/MASTER-PROJECT-STATUS.fa.md` · به‌روز: 2026-10-03

| ID | P | Area | Status | Evidence | Acceptance Test | Dependencies |
|---|---|---|---|---|---|---|
| MB-1 | P1 | Remote/Tailscale | OPEN | سایدکار با `golamirreza1995@` لاگین است؛ میزبان/گوشی روی `rastehnews@` — دو tailnet متفاوت؛ URL ‏`http://100.118.10.107:8766` از دستگاه‌های کاربر باز نمی‌شود | پاک‌کردن `tolid-ts-state` + ورود یک‌باره با rastehnews@؛ سپس ۸ تست راه‌دور (login/dashboard/mutation/logout/dead-session/Host/Origin/CSRF) از گوشی یا لپ‌تاپ | هیچ |
| MB-2 | P2 | Ops/SQLite | OPEN | خواندن `content.sqlite` از میزبان حین اجرای کانتینر → قفل oplock → قطعی موقت ۵۰۰ (در ممیزی 2026-10-03 رخ داد؛ restart وب برگشت) | سند قاعده در RUNBOOK + تست: با استک روشن، بکاپ فقط از داخل کانتینر یا بعد از `docker compose stop`؛ بدون ۵۰۰ | هیچ |
| MB-3 | P2 | Release/Git | OPEN | main (79af4b7 + revert بیرونی) از `recovery/docker-isolation` (5facb3f) جدا است؛ Docker stack روی شاخه اجرا می‌شود | merge بازبینی‌شده به main؛ `git merge-base --is-ancestor` سبز؛ استک روی main بالا بیاید | MB-1 |
| MB-4 | P2 | Tests | OPEN | E2E ‏(24/24) و Smoke ‏(13/13) فقط روی host-native اجرا شده‌اند؛ علیه 18767 نه | `run-e2e.sh` با TEHNET_PANEL_PORT=18767 (بدون سرور موازی) + `smoke-daily.cjs` روی 18767 → سبز | هیچ |
| MB-5 | P2 | SEO/User | OPEN | sitemap tehnet.ir: robots بدون Sitemap، wp-sitemap 404 | فعال‌سازی از wp-admin طبق `docs/SITEMAP-CHECKLIST.fa.md`؛ robots حاوی `Sitemap:` | MB-6 (وردپرس) |
| MB-6 | P2 | Integrations | OPEN | ۱۱ سرویس READY_FOR_CREDENTIAL (۰/۱۱ متصل) — dry-run فقط | برای هر سرویس: Credential + «تست اتصال» سبز + یک عملیات واقعی کم‌ریسک (پیش‌نویس/پیام آزمون) | کاربر |
| MB-7 | P2 | Recording | OPEN | مسیر صوتی فقط با منبع سینتتیک مرورگر تأیید شده | یک ضبط واقعی با میکروفون فیزیکی + ورود موفق به ویزارد | هیچ |
| MB-8 | P3 | Docs | OPEN | README/QUICKSTART هنوز مسیر بومی را main می‌دانند (RUNBOOK به‌روز است) | به‌روزرسانی سه فایل به `Start-Tolid-Docker.cmd` + URL 18767 | MB-3 |
| MB-9 | P3 | Optional | OPEN | Ruflo / Screaming Frog / SERP خارجی نصب نیستند | تصمیم کاربر؛ در صورت نصب: تست اتصال ۱۵ دقیقه‌ای | تصمیم کاربر |
| MB-10 | P3 | Ops | OPEN | فایل نوت رمز (`Tolid-Mohtava-Admin-Credentials.txt`) باید پس از انتقال به مدیر رمز حذف شود | حذف فایل توسط کاربر پس از ذخیره در Password Manager | هیچ |

**خلاصه:** P0=0 · P1=1 · P2=6 · P3=3 · مجموع باز=۱۰
**باگ نرم‌افزاری باز:** ۰ · **Jobهای تاریخی شکست‌خورده (DB واقعی):** ۱ (رفتار کنترلی عمدی) · **Jobهای فعلی شکست‌خورده:** ۰
