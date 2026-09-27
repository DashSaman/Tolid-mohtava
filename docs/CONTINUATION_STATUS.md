# CONTINUATION_STATUS — وضعیت ادامه کار

این فایل Source of Truth ادامه کار است. بعد از هر Milestone به‌روزرسانی و Commit می‌شود تا Session بعدی دقیقاً از همین نقطه ادامه دهد.

- Last updated: 2026-09-27 (session 2 — پایان P0)
- Repo: https://github.com/DashSaman/Tolid-mohtava
- Machine-readable checklist: `docs/implementation-status.json`
- Last commits of this session: 8cb2343 (status files) → 7e804df (jobs) → 5b9f8f5 (media+transcribe) → afca119 (editing) → 1ea51d9 (render) → 6ebf628 (triggers) → d7bbbea (UI) → 2ee5f3c (E2E) → + docs/status update

## Current Phase

Phase 2 تکمیل شد (P0 «Execution واقعی»). فاز بعدی: P1 — repurposing، publishing adapter واقعی (نیاز credential)، website connector، notifications، remote access، storage manager/archive.

## What was built this session (همه با تست و push)

1. **jobs.py** — صف کار ماندگار روی SQLite: queued/running/waiting_approval/completed/failed/cancelled + progress/logs/زمان‌ها/retry_count/error/result + کلید idempotency. بعد از Restart: کارهای running صادقانه failed می‌شوند و queued دوباره اجرا می‌شوند؛ تاریخچه هیچ‌وقت پاک نمی‌شود.
2. **media.py** — ingest تغییرناپذیر صوت/ویدیو با sha256 و جریان streamed (تا 20GB)، انواع voice/screen/face/external_audio/broll، اتصال به محتوا، verify() برای checksum.
3. **transcribe.py** — adapter faster-whisper با تشخیص GPU و fallback خودکار به CPU (خطای cublas در زمان inference هم هندل می‌شود)؛ transcript نسخه‌دار per-media؛ ورود دستی متن با برچسب زمان «1:23 متن» → segments.
4. **editing.py** — تصمیم‌های تدوین غیرمخرب و conservative: سکوت با FFmpeg silencedetect (فعال خودکار ≥0.8s)، فیلرهای مستقل (فعال)، مکث مرزی و تکرار (فقط proposed)؛ restore/dismiss واقعی و پایدار در برابر تحلیل دوباره؛ گزارش فارسی با timestamp قابل Seek؛ timeline() قرارداد رندر.
5. **render.py** — رندر preview (720p) و final (1080p + NVENC در صورت موجودیت + faststart) از برش‌های فعال merge‌شده؛ نسخه‌ها EDIT V1..N / FINAL Vn؛ progress زنده از ffmpeg؛ لغو تعاونی؛ فایل اصلی هرگز تغییر نمی‌کند.
6. **triggers.py** — تأیید انتشار → دقیقاً یک بسته publish_dryrun per content+revision (double-click safe؛ فقط روی گذار واقعی pending→approved)؛ رندر نهایی منتظر تأیید صریح. هیچ انتشار خارجی وجود ندارد.
7. **UI فارسی RTL** — دو صفحه جدید «رسانه و تدوین» و «کارها» به‌همراه دیالوگ جزئیات رسانه (player + نسخه‌های متن با click-to-seek + گزارش تدوین + برش دستی + دکمه‌های رندر + فهرست نسخه‌ها) و صف کار زنده (progress، logs، تأیید/رد/لغو/تلاش دوباره).
8. **tests/test_e2e.py** — مسیر بحرانی کامل روی سیستم واقعی (فقط موتور گفتار fake است تا قطعی باشد): ایده → صوت → متن → تحلیل → restore → preview → dry-run → FINAL (با تأیید) → integrity آرشیو. ۴۷ تست سبز.

## Verified evidence (شواهد واقعی)

- `python -m unittest discover -s tests` → **47/47 OK** (شامل integration واقعی FFmpeg: silencedetect روی فایل صوتی تولیدشده + رندر واقعی با کنترل مدت).
- `node tests/ui-flow.cjs` → PASS با بخش‌های جدید رسانه/کارها (Chrome واقعی).
- تبدیل گفتار واقعی: faster-whisper 1.2.1 روی واو گفتار تولیدشده با SAPI → متن و timestamp دقیق در ۵.۷ ثانیه (device=cpu). CUDA wheels نصب شدند (cublas 12.9/cudnn 9.26) و مسیر GPU فعال می‌شود ولی inference روی GPU خطا می‌دهد و به‌صورت خودکار و صحیح به CPU برمی‌گردد؛ دیباگ GPU به P1 منتقل شد (اولویت اجرایی نیست چون CPU برای مدل small کافی است).
- GPU/FFmpeg/NVENC: `avtools` هر سه را پیدا می‌کند (RTX 3070، FFmpeg 9.0.2، h264_nvenc موجود).

## Environment changes made (برای شفافیت)

- Python 3.12.10 + FFmpeg 9.0.2 با winget نصب شد (پیش‌نیاز اعلام‌شده پروژه؛ روی این ماشین وجود نداشت).
- pip: faster-whisper + nvidia-cublas-cu12 + nvidia-cudnn-cu12 نصب شد (mirror). GPU inference خطای زمان اجرا می‌دهد؛ fallback خودکار CPU صحیح کار می‌کند.

## Remaining P1 (فاز بعد، به‌ترتیب پیشنهادی)

1. Repurposing: استخراج 2-3 کاندیدای Short از transcript + تصمیم‌ها؛ برش عمودی با layout آموزشی (نه crop کور).
2. Publishing adapter واقعی (Postiz یا custom) — نیاز به credential/تصمیم کاربر؛ تا آن زمان dry-run جاری می‌ماند.
3. Website connector برای tehnet.ir / mytel.ir (اول کشف CMS).
4. Notifications: Telegram (نیاز TELEGRAM_BOT_TOKEN) + ایمیل.
5. Storage Manager + آرشیو روی My Passport با checksum و تأیید (هرگز حذف خودکار).
6. Remote access با Tailscale/Cloudflare Tunnel + حداقل auth (user/pass هش‌شده).
7. Media Sync چند دوربین (فیس‌کم/صفحه/صدای جدا) با waveform/timestamp.
8. رفع خطای GPU whisper روی این ماشین (احتمال ناسازگاری cuDNN/درایور) و افزودن انتخاب مدل در UI.

## Remaining P2

Analytics ingestion (نیاز OAuth)، weekly analysis، adaptive scheduling، post-publish optimization، learning loop، weekly ideas، SEO خودکار سایت‌وار.

## Required Credentials (فقط این‌ها از کاربر)

- OAuth پلتفرم‌ها برای انتشار/Analytics واقعی.
- TELEGRAM_BOT_TOKEN + chat id برای اعلان.
- GOOGLE_AI_API_KEY برای رندر Gemini (thumbnail/carousel/infographic).

## Known Issues / نکته‌ها

- `py -3` و `python` در PATH ویندوز تازه نصب شده‌اند؛ Open-Panel.cmd باید کار کند (تست دستی نشده چون پنل با تست‌ها و سرور آزمایشی پوشش داده شده).
- مدلی که میدل transcribe استفاده می‌کند 'small' است؛ برای فارسی مدل medium/large-v3 کیفیت بهتر می‌دهد (کندتر). پیکربندی مدل هنوز در UI نیست (payload job آن را می‌پذیرد).
- تست مرورگر بخش رسانه به TEHNET_FFMPEG نیاز دارد (در پیام commit قبلی مستند شد؛ در TECHNICAL.md هم هست).
- CSP اجازه style inline نمی‌دهد؛ progress barها از CSSOM استفاده می‌کنند (الگوی موجود را نگه دارید).
