# CONTINUATION_STATUS — وضعیت ادامه کار

این فایل Source of Truth ادامه کار است. بعد از هر Milestone به‌روزرسانی و Commit می‌شود تا Session بعدی دقیقاً از همین نقطه ادامه دهد.
This file is the handoff source of truth. Update + commit after every milestone.

- Last updated: 2026-09-27 (session 2 — continuation)
- Last successful commit: (به‌روزرسانی بعد از هر push — see git log)
- Repo: https://github.com/DashSaman/Tolid-mohtava
- Machine-readable checklist: `docs/implementation-status.json`

## Current Phase

Phase 2 — «Execution واقعی»: تبدیل پنلِ فقط-Prompt به Panel → Job → Worker → Result (مطابق master-prompt بند ۹ و ۶۲).

## State Recovery Matrix (نتیجه Audit واقعی Session دوم)

روش: clone تازه از origin/main، بررسی git log (فقط ۲ commit)، خواندن کد واقعی `outputs/panel/*.py`، `app.js`، `index.html`، تست‌ها و مستندات. هیچ قابلیتی از روی README حدس زده نشده.

### WORKING (با تست؛ فقط تست موفق = Working)

| قابلیت | شواهد |
|---|---|
| دفتر محتوا (CRUD، نسخه‌گذاری، تفکیک برند) | `store.py` + `tests/test_store.py` |
| تأیید نسخه‌دار سناریو/انتشار، idempotent در همان حالت، ابطال با ویرایش | `store.decide` + تست‌ها |
| تاریخچه snapshot و export JSON | `store.history/export` |
| نصب pinned ۱۷ اسکیل با کنترل hash | `scripts/install_skills.py` + `tests/test_install.py` |
| بسته دستور فارسی هر اسکیل (Manual Prompt Mode) | `app.js makePrompt` |
| سرور HTTP محلی با کنترل Host/Origin/Token و CSP | `server.py` + `tests/test_http.py` |
| Backup دیتابیس | `backup.py` + `Backup-Panel.cmd` |

### PARTIAL

| قابلیت | وضعیت واقعی |
|---|---|
| Transcript | فقط ورود فایل TXT/MD دستی؛ هیچ صوت→متن نیست |
| Analytics | فقط زبانه خالی + بسته دستور؛ هیچ ingestion |
| SEO | چک‌لیست ثابت؛ crawl ندارد |
| اعلان‌ها | فقط فهرست داخل پنل؛ Telegram/Email وصل نیست |

### NOT STARTED (شروع نشده — Session قبلی متوقف شد)

Job system، آپلود صوت، transcription، media ingest، media sync، automatic editing، edit decisions غیرمخرب، restore، edit report، transcript timeline، render، media versions، storage manager، archive، repurposing، publishing adapter، website connector، یادگیری/بهینه‌سازی، remote access، authentication.

### BLOCKED (نیاز به Credential/تصمیم کاربر)

- انتشار واقعی هر پلتفرم (OAuth حساب‌ها) — طبق بند ۳۵ فعلاً فقط Dry Run.
- Analytics واقعی (API حساب‌ها) — credential لازم.
- Gemini/Apify برای thumbnail/carousel/infographic render — `BLOCKED_BY_CREDENTIAL`.
- Telegram/Email notification — `TELEGRAM_BOT_TOKEN`/SMTP لازم.

## Environment Reality (کشف‌شده در این Session)

- Windows: Python واقعی در PATH نبود (فقط Store stub) → Python 3.12 با winget نصب شد (پیش‌نیاز اعلام‌شده README).
- FFmpeg: در Windows و WSL موجود نبود → نصب شد (برای audio pipeline و render؛ بند ۲۲ و ۲۴).
- WSL Ubuntu-24.04: Python 3.12.3 موجود؛ faster-whisper نصب نبود.
- GPU: NVIDIA GeForce RTX 3070 Laptop 8GB (driver 616.92) — برای transcription/render در صورت سازگاری استفاده می‌شود.
- Node v24.19.0 موجود (تست UI).
- این Session برخلاف Session قبلی به WSL دسترسی دارد (`wsl.exe -l -v` جواب داد).

## Last Tests

- (بعد از نصب Python اجرا و اینجا ثبت می‌شود.)

## Remaining P0 (به‌ترتیب اجرا)

1. `jobs.py` — Job system با SQLite (states: queued/running/waiting_approval/completed/failed/cancelled + progress/logs/timestamps/retry/error/result) و بقا پس از Restart.
2. Media ingest — آپلود صوت/ویدیو، جدول media، فایل‌های اصلی immutable، gitignored.
3. Transcription worker — engine adapter؛ faster-whisper در صورت نصب (GPU در صورت سازگاری)؛ در نبودش شکست صادقانه `BLOCKED_BY_DEPENDENCY` — هیچ transcript جعلی.
4. Automatic editing — تشخیص conservative سکوت/مکث/فیلر/تکرار/retake؛ decisionها جدا از media (غیرمخرب)؛ edit report فارسی؛ restore واقعی.
5. Render — preview و final با FFmpeg؛ NVENC در صورت موجودیت؛ media versions (RAW/EDIT V1..N/FINAL).
6. Approval triggers — تأیید → Job بعدی، idempotent با کلید یکتا.
7. UI فارسی صفحات Jobs/Media + تست مرورگر.

## Remaining P1

Repurposing (candidate shorts)، package عنوان/هوک/کاور به‌صورت داده، publishing adapter (dry-run اول)، website connector، notifications، remote access (Tailscale/Cloudflare Tunnel موجود)، storage manager، archive روی My Passport با checksum و approval.

## Remaining P2

Analytics ingestion، weekly analysis، adaptive scheduling، post-publish optimization، learning loop، weekly ideas، site-wide SEO automation.

## Required Credentials (فقط همین‌ها از کاربر)

- برای انتشار واقعی/Analytics: OAuth هر پلتفرم.
- برای Telegram: bot token + chat id.
- برای Gemini render: GOOGLE_AI_API_KEY در secret manager.

## Known Issues

- DB مسیر پیش‌فرض `outputs/panel/data/content.sqlite`؛ در `.gitignore` است (درست).
- `py -3` در Windows فعلی موجود نبود تا نصب winget؛ Open-Panel.cmd مسیر `python` را فرض می‌کند.
- تست مرورگر `tests/ui-flow.cjs` به Playwright/Chrome موجود وابسته است؛ در این محیط باید راستی‌آزمایی شود.
