# Work log / سابقه کار

## 2026-09-26 — Original workstation work

1. Read the supplied 53-section master prompt and confirmed scope: install 17 skills and deliver a local Persian panel without changing existing services.
2. Inspected available Windows commands and project directories. Found GrowthOS scripts, a local DashSaman/-SEO reference checkout, LM Studio/model folders and existing Codex tools.
3. WSL enumeration returned E_ACCESSDENIED. Docker was not in Windows PATH; absence inside WSL was not inferred. Recorded service ports refused connections from the audit environment.
4. Retrieved the upstream repository at a fixed commit and reviewed all 17 actual SKILL.md files.
5. Wrote a 13-part Persian audit, capability/overlap/gap mapping, canonical policy, and two brand profiles. Explicit requested tone was recorded without pretending writing samples had been analyzed.
6. Installed all 17 skills globally with Codex's existing skill-installer helper; verified all 19 files byte-for-byte against upstream. No LLM, Docker service, provider SDK, paid scrape or new browser was installed.
7. Built a local Persian RTL panel with standard-library Python and SQLite. Implemented brand-aware content, history, version-specific script/publication decisions, prompt packages and JSON export.
8. Ran storage, HTTP and real-browser tests. Reviewed desktop/mobile screenshots. Created a SQLite backup of the initially empty panel.
9. Reported limitations: no audio conversion, editing, connected model execution, social publishing, external notification delivery or live analytics.

## 2026-09-26 — Repository handoff

- Confirmed the requested public GitHub repository was empty before adding files.
- Added source, audit, policy, profiles, tests, screenshots and unchanged third-party skills/license.
- Excluded real runtime databases, backups, temporary data, credentials and workstation-specific home paths.
- Made installation and startup portable; preserved the live workstation panel unchanged.
- Added actual per-machine skill detection to avoid treating a clone as an installed environment.
- Added full Persian/English README coverage for every section, field, button, skill and existing service.
- Preserved the original verification report as historical evidence; repository-specific checks are recorded in REPOSITORY-VERIFICATION.md.

## Deferred / انجام‌نشده

Complete WSL/container audit; provider and account integrations; audio transcription; video editing; publication job queue and retry/idempotency; email/Telegram notifications; real analytics ingestion and scheduling optimization. No provider credentials are required merely to run the local panel.

## 2026-09-27 — Continuation session: from prompt factory to execution

1. State recovery audit against origin/main (2 commits, no continuation files existed). Recorded the matrix in docs/CONTINUATION_STATUS.md and docs/implementation-status.json; both now update every milestone.
2. Environment reality: installed Python 3.12 + FFmpeg 9.0.2 (winget) because the panel prerequisite was missing on Windows; WSL access restored; RTX 3070 detected; faster-whisper 1.2.1 installed for local Persian STT.
3. Job system (jobs.py): SQLite-backed queue with progress/logs/retry/cancel/approval gates, idempotency keys, restart recovery. Tested.
4. Media ingest (media.py): immutable originals with sha256, kind taxonomy, content linkage; token-gated 20GB raw upload; ranged streaming playback.
5. Transcription worker: faster-whisper adapter with GPU detection and honest BLOCKED_BY_DEPENDENCY failure; per-media versioned transcripts; manual timed-text entry.
6. Automatic editing (editing.py): conservative decisions — silence via FFmpeg silencedetect, standalone fillers auto-cut; borderline pauses and repeats only proposed; restore/dismiss are real state changes that survive re-analysis; Persian report with seekable timestamps.
7. Render pipeline (render.py): preview + NVENC final from merged active cuts, versions EDIT V1..N/FINAL, live progress, cooperative cancel; originals untouched.
8. Approval triggers: publish approval enqueues exactly one DRY RUN package per revision; final render waits for explicit approval. No external publish exists.
9. Persian RTL UI: media editing room and live jobs pages wired to the real workers; browser test extended and passing.
10. End-to-end fixture test runs the critical path on the real job system and real FFmpeg (only the speech engine is substituted for determinism).

## 2026-09-30 — v1.0.0-local-ready (Release)

نسخهٔ نهایی محلی. توسعهٔ محلی از این نقطه FROZEN است؛ تغییرات بعدی فقط برای باگ واقعی کاربر یا شکست اتصال Credential.

### قابلیت‌های کامل‌شده (به‌ترتیب تاریخی جلسات)

- **پلتفرم پایه:** پنل فارسی RTL فقط-محلی (Python stdlib + SQLite WAL روی loopback)، صف کار پایدار با idempotency و retry cap، بازیابی صادقانه پس از ری‌استارت، سازهٔ غیرمخرب RAW + sha256.
- **AI محلی:** اتصال LM Studio (Qwen2.5-7B پیش‌فرض)، مسیر هوش مصنوعی پروژه (تحقیق/بررسی فنی/سناریو/هوک/بسته‌ها/مقاله/کامنت پین/خط تولید کامل)، ۱۷ اسکیل نصب‌شده، موتور بهینه‌سازی محتوا (SEO/AEO/GEO) و KB داخلی.
- **رسانه و صدا:** faster-whisper فارسی (medium، fallback خودکار CPU)، تست بزرگ ۴۷۸MB واقعی سبز، ضبط مرورگری با انتخاب میکروفون/تست واقعی/سطح زنده/اعتبارسنجی INVALID_AUDIO/ضبط مجدد نسخه‌دار.
- **تدوین غیرمخرب:** silencedetect + تصمیم‌های active/proposed/dismissed، حکم کاربر در تحلیل دوباره می‌ماند، رندر Preview/FINAL با NVENC.
- **Shorts:** کاندیدا از transcript واقعی + رندر ۹:۱۶ با پس‌زمینه محو (این release دو باگ واقعی آن رفع شد — پایین‌تر).
- **سئو/Analytics:** اسکن سایت + پیشنهاد اصلاح، هضم GSC/GA4 (با Credential)، اسنپ‌شات append-only، زمان‌بندی تطبیقی BASELINE→DATA_DRIVEN، برنامهٔ هفتگی مبتنی بر شواهد.
- **انتشار:** فقط Dry-Run بدون Credential؛ پیش‌نویس وردپرس (فقط DRAFT) با Application Password؛ اتصالات OAuth پایه‌گذاری شد (YouTube/Meta/LinkedIn) — همه BLOCKED_BY_CREDENTIAL تا ورود کلیدهای واقعی.
- **امنیت:** احراز هویت اختیاری ADMIN_* (PBKDF2، نشست ۱۲h، rate-limit)، CSRF/Origin gating، ماتریس ۹/۹؛ ممیزی نشت Secret = ۰.
- **بکاپ/ری‌استور:** Backup/Restore-TolidMohtava.ps1 با checksum، تست ایزوله سبز.
- **UI v3:** طراحی شیشه‌ای آرام RTL، ۲۲ مسیر، موبایل ۳۹۳px، مرکز اتصال‌های صادقانه (۱۱ کارت).
- **فریز:** گزارش PROJECT-FREEZE، آماده‌سازی ۹۵٪، تست‌های نهایی 125/125 + E2E 24/24 + Smoke 13/13.

### باگ‌های واقعی که در همین release پیدا و رفع شد (UAT کلیکی)

1. **Shorts render کاملاً خراب بود** — دو عامل: آدرس فایل خروجی به دستور FFmpeg اضافه نمی‌شد (هر رندر ۹:۱۶ fail می‌شد؛ E2E فقط رتبه‌بندی کاندیدا را می‌سنجید نه رندر) و نبود `-nostdin` باعث بلاک‌شدن FFmpeg پس از اتمام در محیط پنل می‌شد. رفع: افزودن خروجی + `-nostdin`؛ تأیید با رندر واقعی 1080×1920 در سفر کاربر.
2. **بازگردانی از آرشیو در UI غیرممکن بود** — دکمهٔ بازگردانی فقط برای ردیف‌های آرشیوشده رندر می‌شد اما هیچ فهرستی آیتم‌های آرشیوشده را واکشی نمی‌کرد (کد مرده). رفع: دکمهٔ «نمایش آرشیو» در صفحهٔ پروژه‌ها + کارت آرشیو با همان جریان بازگردانی.

### شناخته‌شده (غیرمسدودکننده، بدون تغییر در این release)

- فهرست‌های داشبورد/پروژه‌ها پس از ساخت پروژه در ویزارد بدون رفرش (F5) تازه نمی‌شوند؛ با باز کردن پروندهٔ پروژه یا F5 درست می‌شوند.
- کلیک دکمهٔ «تبدیل گفتار به متن» یک‌بار اضافی enqueue می‌کند (onclick تب + هندلر سراسری)؛ idempotency کلید یکسان در حالت race دو job موازی می‌سازد — نتیجه یکی است، فقط محاسبهٔ اضافه.

### خارج از محصول (نیازمند کار/کلید کاربر)

- ۱۱ Credential بیرونی (وردپرس ×2، Telegram، YouTube، Instagram، Facebook، LinkedIn، GSC، GA4، Google Ads، Gemini) — راهنما: CREDENTIAL-ONBOARDING.fa.md
- فعال‌سازی sitemap tehnet.ir از wp-admin (SITEMAP-CHECKLIST.fa.md)
- تست میکروفون فیزیکی
- ابزارهای اختیاری (Ruflo / Screaming Frog / SERP خارجی) — پنل بدون آن‌ها کامل است.


## 2026-09-30 — v1.1.0-ui-rc1 (72h Polish & Hardening Sprint)

### سخت‌افزاری/قابلیت پایداری (Day 1)
- فهرست‌ها دیگر F5 نمی‌خواهند (route روی صفحات داده‌محور Core را تازه می‌کند).
- enqueue هم‌کلید اتمیک شد (ایندکس UNIQUE + مدیریت IntegrityError؛ اثبات ۴۸-ترد = ۱ job).
- دکمهٔ «تبدیل گفتار به متن» دیگر دوبار fire نمی‌شود (حذف binding تکراری تب).
- **ریشهٔ مرگ Shorts کشف و رفع شد:** libx264 آمار را به stderr می‌ریزد و pipe خوانده‌نشدهٔ ۶۴KB وسط انکود پر می‌شد → دیداک‌لاک. stderr→فایل موقت (+ همان اصلاح در render.py برای مسیر CPU). تأیید: رندر ۹:۱۶ از ~۲۲۰ث/هنگ → **۴ ثانیه**.
- پنجرهٔ کاندیدای Shorts به مدت رسانه clamp شد (کاندیدای عبوری از EOF حالا بخش واقعی باقی‌مانده را می‌سازد).
- FFmpeg های shaات‌گر با watchdog + اعتبارسنجی ffprobe مهار می‌شوند (خط دفاعی دوم).

### هویت بصری v4 «اتاق فرمان سیگنال» (Day 2)
- بازطراحی کامل: ink-navy تیره، سطوح لایه‌ای solid، اکسنت azure/teal با صرفه، اعداد mono.
- دو موتیف اختصاصی: نوار سیگنال موجی + کانال‌های جریان خط‌چین (فقط نود فعال متحرک).
- داشبورد فرمانی: پنل «نیازمند توجه شما»، CTA آخرین پروژه، چیپ‌های صادقانهٔ AI/GPU.
- پذیرش بصری اسکرین‌شاتی: ۲۷ کپچر واقعی، ۰ خطای کنسول، ۱ بازنگری (از ۲ مجاز).
- قوانین طراحی مکتوب: DESIGN-SYSTEM.fa.md + UI-COMPONENT-INVENTORY.md.

### پذیرش (Day 3)
- سفر کاربر: **۴۴/۴۴** · تور مسیرها: **۲۰/۲۰** · Unit **125/125** · E2E **24/24** · Smoke **13/13**.
- پرفورمنس: تعامل اول 461ms، ناوبری 46-314ms، حافظهٔ JS 4MB.
- رسانهٔ بزرگ: 1.01GB/۳۰min کامل (آپلود 2.1s، Whisper 27s با VAD، kill/restart/retry، رندر، Short).
- همزمانی: hammer هم‌کلید=۱، بدون lock/dup/lost؛ حجم داده: ۱۰۰ پروژه، لیست‌ها 4-35ms.
- تزریق خطا: 401/403/429/500/timeout/LM-down/رسانهٔ خراب — همگی خطای فارسی صادقانه.
- امنیت: traversal/filename/CSRF/origin/oversized/OAuth-replay/delete-race — همه PASS.
- بکاپ/ری‌استور روی دادهٔ واقعی: PASS.
