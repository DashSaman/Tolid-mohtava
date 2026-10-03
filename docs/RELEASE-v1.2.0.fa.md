# Release v1.2.0 — کارخانهٔ محتوا Tolid-Mohtava (۲۰۲۶-۱۰-۰۳)

## وضعیت: CORE SOFTWARE ۱۰۰٪ — آمادهٔ تولید محتوای واقعی

## معماری Docker
- **سرویس‌ها:** `tolid-web` (پایتون ۳.۱۲ لینوکسی، non-root uid 10001، HEALTHCHECK) + `tolid-tailscale` (سایدکار رسمی v1.102.4، NET_ADMIN+tun، state volume خودش) — شبکهٔ `tolid_internal`، بدون host-network/privileged/docker-socket.
- **لوکال:** فقط `127.0.0.1:18767 → 8766/کانتینر` (هرگز 0.0.0.0؛ پورت 8766 میزبان متعلق به AutoClaw و استفاده نشده).
- **دیتابیس:** SQLite ‏WAL در volume نام‌دار `tolid-db-data` (فایل‌سیستم بومی لینوکس؛ ریشهٔ مشکل oplock بایند‌ماونت ویندوزی رفع شد). media/renders همان bind میزبان (RAW جابه‌جا نشد).
- **سِکرِت:** `runtime/secrets/tolid.env` (گیت‌ایگنور) — فقط ADMIN_USER + ADMIN_PASSWORD_HASH ‏(PBKDF2-120k).
- **راه‌اندازی روزمره:** `Start-Tolid-Docker.cmd` · توقف: `Stop` · وضعیت: `Status`.

## AI/رسانه
- **LM Studio:** روی میزبان (127.0.0.1:1234)؛ کانتینر از `host.docker.internal` (روشن‌سازی امن با `lms.exe server start`)؛ تولید واقعی از درون کانتینر ✓ (qwen2.5-7b، ۳ مدل).
- **Whisper:** faster-whisper 1.2.1 + av==18.1.0 (پین host-proven) — CPU؛ رندرهای واقعی فارسی ۵ قطعه ✓.
- **FFmpeg:** 7.1.5 درون‌کانتینر؛ ریشهٔ دیادلاک Shorts (pipe stderr) با stderr→فایل + watchdog + clamp حفظ شد.
- **GPU:** CPU_FALLBACK صادقانه (runtime موجود، image بدون CUDA libs؛ رندر libx264).

## امنیت و راه‌دور
- auth اجباری + CSRF/Host/Origin (whitelist لوکال-هر-پورت + `tolid-web` + `.ts.net` + tailnet ‏v4/v6 با دفاع DNS-rebinding دست‌نخورده)؛ بازیابی خودکار صفحهٔ کهنه پس از restart.
- **راه‌دور:** فقط سایدکار Tailscale در همان tailnet شما (rastehnews@)؛ مسیر IPv6 ‏tailnet (socat دو-پشته) — `http://[fd7a:115c:a1e0::2a:e801]:8766`؛ **Funnel خاموش**؛ بدون پروکسی میزبانی/قاعدهٔ فایروال Tolid/اعتبارنامهٔ Registry.

## پذیرش نهایی (همه روی رانتایم Docker فعلی)
- Automated **127/127** · E2E **24/24** (پس از DEPENDENCY_OFFLINE_RESOLVED: سرور LM با CLI رسمی روشن شد و ۳ گام وابسته سبز شدند؛ ریشهٔ e2e هم URL پروایدر 127.0.0.1→host.docker.internal شد) · Smoke **13/13**.
- **سفر مرورگر واقعی ۲۵/۲۵** (ورود…حذف؛ Whisper/Preview/Final گیت‌دار/Short/Article/LM واقعی).
- **Auth مرورگر ۶/۶** · **Remote ۸/۸** · SQLite integrity=ok + بکاپ API حین اجرا.
- jobهای فعلی: ۱۴ شکست‌خورده = ۱۲ LM-off تاریخی (زمان خاموشی سرور) + ۱ empty-transcript کنترلی + ۱ باگ hooks (رفع شد در 39d7900 و زنده تأیید شد؛ اثر: ۶ هوک).

## کارهای کاربر (مسدودکنندهٔ بیرونی، نه داخلی)
۱۱ Credential بیرونی (وردپرس×۲/تلگرام/YT/IG/FB/LI/GSC/GA4/Ads/Gemini — راهنما: `docs/CREDENTIAL-ONBOARDING.fa.md`) · میکروفون فیزیکی · sitemap tehnet.ir از wp-admin (robots 200 بدون Sitemap؛ wp-sitemap 404؛ `docs/SITEMAP-CHECKLIST.fa.md`).

## اختیاری (پنل بدون آن‌ها کامل است)
Ruflo · Screaming Frog · SERP خارجی.

## بکاپ/بازگردانی و Rollback
- بکاپ release: `backups/content-final-20261003-195943.sqlite` (sha256 ‏`c4e0fcb1…f2f99fc`، integrity ok) — مکانیزم روزمره: `Backup-Tolid-Docker.cmd` / `Restore-Tolid-Docker.cmd`.
- **Rollback کامل:** تگ `v1.1.0-ui-rc1` (+ `v1.2.0-docker-rc1` به‌عنوان مرجع RC داکر)؛ `docker compose stop` + اجرای بومی `Open-Panel.cmd` (فقط rollback).
