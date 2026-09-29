# CONTINUATION_STATUS — وضعیت ادامه کار

این فایل Source of Truth ادامه کار است. بعد از هر Milestone به‌روزرسانی و Commit می‌شود تا Session بعدی دقیقاً از همین نقطه ادامه دهد.

- Last updated: 2026-09-27 (session 2 — P0 + بازطراحی محصول UI)
- Last commits of UI milestone: (see git log — «product: professional Persian RTL UI…»)
- Repo: https://github.com/DashSaman/Tolid-mohtava
- Machine-readable checklist: `docs/implementation-status.json`
- Last commits of this session: 8cb2343 (status files) → 7e804df (jobs) → 5b9f8f5 (media+transcribe) → afca119 (editing) → 1ea51d9 (render) → 6ebf628 (triggers) → d7bbbea (UI) → 2ee5f3c (E2E) → + docs/status update

## Current Phase

Phase 2 تکمیل شد و کل P0 از طریق UI قابل استفاده است (تست مرورگر جامع PASS). فاز بعدی در زمان نگارش P1 بود؛ همهٔ آن موارد اکنون تکمیل شده‌اند (Sections پایین‌تر).

## UI Product Milestone (جلسه دوم - بازطراحی)

- علت «ظاهر خام HTML»: باز کردن مستقیم index.html از دیسک (file://) که در آن style/app/api بارگذاری نمی‌شوند. راه‌حل: مسیرهای نسبی + گارد file:// با پیام راهنمای فارسی + سخت‌سازی Open-Panel.cmd (یافتن python از سه مسیر + باز کردن خودکار http://127.0.0.1:8766).
- بازطراحی کامل UI: سیستم طراحی RTL (Vazirmatn self-hosted، توکن‌های رنگ، کارت/جدول/badge/tabs/stepper/toast/skeleton)، نوار کنار گروه‌بندی‌شده با ۲۱ بخش، داشبورد واقعی، ویزارد ۴ مرحله‌ای «تولید محتوا» (شامل ضبط مستقیم از میکروفون با MediaRecorder)، صفحه پروژه ۱۲ تبی با خط زمان، فضای تدوین، نسخه‌ها، Shorts (کاندیدای واقعی از transcript + رندر ۹:۱۶ با پس‌زمینه محو)، تصاویر (آپلود + تأیید؛ تولید BLOCKED Credential)، مرکز تأیید واقعی، انتشار، کارها (جدول + فیلتر)، Storage واقعی (درایوها + My Passport E:\ شناسایی شد)، سلامت سیستم واقعی + آزمون GPU.
- GPU root cause پیدا و رفع شد: ctranslate2 روی Windows با LoadLibrary ساده cublas64_12.dll را load می‌کند؛ add_dll_directory کافی نیست و پوشه باید در PATH باشد. نتیجه: transcription 2.8s روی RTX 3070 (cuda) در مقابل 5.7s CPU.
- تست مرورگر جدید (tests/ui-flow.cjs) کل سفر کاربر را در UI واقعی اجرا می‌کند: ویزارد ← آپلود صوت ← transcription واقعی ← transcript ← ذخیره/تأیید سناریو ← آپلود رسانه ← متن دستی ← تحلیل تدوین ← بازگردانی برش ← رندر preview (پخش 206) ← تأیید رندر نهایی ← تأیید انتشار ← dry-run ← صفحات jobs/storage/health ← نمای موبایل. خروجی: بدون خطای console. اسکرین‌شات‌ها در docs/images/ به‌روزرسانی شدند.

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

## Session 3 (2026-09-28) — لایهٔ هوش محتوا (AI Brain) + اعلان‌ها

### راستی‌آزمایی شکاف‌ها (Phase 0 — با کد/سرویس واقعی)
- LM Studio: نصب بود، سرور خاموش؛ بک‌اند انتخابی (cuda12-2.14.0) به‌خاطر DLL خراب بارگذاری نمی‌شد → **بک‌اند Vulkan روی GPU RTX 3070 فعال شد** (فایل backend-preferences-v1.json) و مدل واقعاً روی GPU اجرا می‌شود.
- meta-llama-3-8b-instruct: برای فارسی نامناسب است (توکنایزر فارسی ندارد) → دانلود Qwen2.5-7B-Instruct (فارسی‌توان) آغاز شد.
- Ollama/LiteLLM/OpenHands: هیچ‌کدام نصب/فعال نبودند (پورت‌ها بسته؛ فایل‌های GrowthOS فقط ارجاع تاریخی‌اند). REUSE شد: LM Studio به‌عنوان provider محلی.
- DeepSeek-R1-Qwen3-8B: دانلود ناقص از قبل (۵۳۷MB از ۵GB) — قابل استفاده نبود.

### ساخته شد (تست‌شده و push شده)
1. **ai.py** — لایهٔ چند-پرووایدر OpenAI-compatible: LM Studio/Ollama/ریموت؛ مسیریابی وظیفه (research/verification/script/social/seo/analysis/hooks/thumbnail)؛ بررسی سلامت واقعی؛ **Credential فقط با نام متغیر محیطی** (هیچ کلیدی در DB نیست)؛ استخراج مقاوم JSON از مدل‌های کوچک.
2. **skill_router.py** — ۱۷ فایل SKILL.md واقعی به دانش اجرایی پرامپت تبدیل شد (نگاشت مرحله→اسکیل + طبقه‌بندی صادقانه AUTOMATED/ASSISTED/MANUAL/BLOCKED_BY_CREDENTIAL).
3. **ai_jobs.py** — کارهای اجرایی روی Worker موجود: تحقیق موضوع (با **بررسی HTTP واقعی منابع** → live/dead + NEEDS VERIFICATION)، راستی‌آزمایی فنی، **سناریوی کامل فارسی با مارکرهای ساختاری** ([FACE CAM] و…)، هوک‌ها (۶ زاویه)، بسته‌های عنوان/هوک/کاور (A پیشنهاد Agent + ۳ جایگزین؛ چهره ۳۰-۵۰٪؛ بدون کلیک‌بیت؛ رنگ رسمی جعل نمی‌شود)، نسخهٔ شبکه‌ها (CTA قاعده‌مند: VoIP→MyTel زمینه‌ای، VPN→اشتراک/tehnet.ir)، مقاله+سئو از transcript، کامنت پین، و **خط تولید کامل** صوت/ایده تا بسته‌ها با توقف در waiting_approval.
4. **قواعد برند در کد**: ستون‌های تهران نتورک، اهمیت راهبردی VoIP برای MyTel، حفظ محتوای VPN، و **حریم خصوصی PVNetwork** (هرگز مالکیت/ارتباط رسمی ذکر یا استنباط نشود).
5. **UI**: تب «هوش مصنوعی» در صفحه پروژه (دکمه‌های خط تولید + خروجی‌ها + منابع زنده/نیازمند بررسی + ثبت سناریو به‌عنوان نسخهٔ تازه با تأیید) و کارت Providerها در تنظیمات (بررسی سلامت، کلیدها mask شده، طبقه‌بندی اسکیل‌ها).
6. **notifications.py** — مرکز اعلان: رویدادهای معنادار (شکست کار، نیاز به تأیید، رندر/کار هوشمند کامل) توسط watcher ثبت می‌شود؛ آداپتور Telegram با TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID (بدون credential: صادقانه BLOCKED_BY_CREDENTIAL)؛ صفحه اعلان‌ها با خوانده‌نشده و دکمهٔ آزمون.
7. **تست‌ها**: ۸ تست AI با LLM fake قطعی (شامل شکست صادقانه بدون provider، ذخیرهٔ parse_error، بررسی واقعی URL، خط تولید کامل) + ۲ تست اعلان = **۵۷/۵۷**.
8. **E2E واقعی**: سرور زنده ← صف کار ← LM Studio (GPU) ← تولید واقعی ۶ هوک فارسی برای موضوع MikroTik ← ذخیره با متادیتای provider/model. (خروجی قابل‌قبول فارسی؛ کیفیت بالاتر با Qwen.)

### مدل محلی
- فعال: meta-llama-3-8b-instruct (Vulkan/GPU) — فارسی قابل‌خواندن ولی متوسط.
- در حال دانلود: **Qwen2.5-7B-Instruct Q4_K_M** (فارسی‌توان). بعد از تکمیل: در تنظیمات پنل، مدل provider lmstudio را qwen2.5-7b-instruct بگذارید.

## Session 4 (2026-09-28) — سخت‌سازی عملیاتی (Priorities 1-18 از پرامپت چهارم)

### راستی‌آزمایی + تکمیل‌ها (همه تست‌شده و push شده — ۶۷/۶۷ تست)
1. **کنترل Whisper + بنچمارک واقعی فارسی (P1/P2)** — `whisper_config.py`: انتخاب مدل (small/medium/large-v3) ماندگار در پنل؛ نمونهٔ گفتار فارسی واقعی با edge-tts (fa-IR-FaridNeural) تولید و بنچمارک شد: **small: 2.1s، RTF 0.09، هم‌پوشانی ~۵۹٪ · medium: 2.7s، RTF 0.11، هم‌پوشانی ~۷۶٪ (هر دو روی CUDA)** → پیش‌فرض این دستگاه: **medium** (مستند در جدول بنچمارک UI؛ قابل تغییر).
2. **همگام‌سازی چند-ترکه (P3)** — `sync.py`: correlation پوش انرژی + تشخیص کلپ/ترنزینت + امتیاز اطمینان + افست دستی؛ آفست‌ها متادیتای پروژه‌اند (RAW دست نمی‌خورد)؛ کار `sync_content` + UI در تب رسانه (نمایش افست/اطمینان و هشدار بازبینی زیر ۶۰٪).
3. **بهبود محافظه‌کارانهٔ صوت (P4)** — زنجیرهٔ ملایم FFmpeg (highpass 80 + afftdn + compressor + loudnorm) → فایل NEW با برچسب ENHANCED Vn؛ RAW تغییرناپذیر.
4. **موتور سئوی سایت (P6)** — `seo_engine.py`: خزش واقعی محدود (sitemap + تا ۲۵ صفحه): robots/sitemap/title/meta/canonical/h1/alt/عنوان‌ها و توضیحات تکراری/لینک خراب نمونه‌ای؛ **هر اسکن تاریخچهٔ جداگانه** (بازنویسی ممنوع). *E2E واقعی روی tehnet.ir: ۲۴ صفحه، ۳۱ مشکل، sitemap ناموجود (404) — یافتهٔ قابل‌اقدام!*
5. **احراز هویت (P16)** — `ops.py`: ADMIN_USER/ADMIN_PASSWORD (یا HASH) در environment → PBKDF2 + نشست + rate limit ورود (۸ تلاش/۵ دقیقه). بدون env: رفتار loopback قبلی. دسترسی راه دور: Tailscale توصیه‌شده؛ پورت 8766 هرگز عمومی نشود.
6. **آرشیو My Passport (P17)** — کار `archive_copy`: منتظر تأیید ← کپی ← تأیید checksum (sha256 با رکورد رسانه) ← **حذف SSD فقط با تأیید جداگانه**؛ قطع بودن دیسک: خطای صادقانه.
7. **مرکز اتصال حساب‌ها (P18)** — کارت یکپارچه در تنظیمات: وضعیت هر ادغام (WP دو سایت، شبکه‌های اجتماعی، GSC، Gemini، Telegram) + نام دقیق متغیر محیطی + بدون نمایش Secret.
8. **رفع flaky تست‌ها** — کلید idempotency اکنون سخت‌گیرانه است (همان کلید=همان کار در هر وضعیتی؛ اجرای دوباره فقط با retry صریح). ۳× پشت‌سرهم ۶۷/۶۷.
9. **UI**: کارت Whisper با جدول بنچمارک زنده و دکمهٔ اجرای بنچمارک، دکمهٔ بهبود صوت در فضای تدوین، صفحهٔ سئو با اسکن/تاریخچه، دکمهٔ آرشیو در فضای ذخیره‌سازی.

### مدل محلی (وضعیت صادقانه)
- فعال و تست‌شده: meta-llama-3-8b (Vulkan/GPU) — هوک فارسی واقعی تولید کرد؛ برای متن بلند فارسی کیفیت متوسط.
- **Qwen2.5-7B-Instruct** (فارسی‌توان، پیشنهادی): دانلود روی این شبکه بسیار کند بود و کامل نشد. ازسرگیری: `lms get "qwen2.5-7b-instruct@q4_k_m"` و سپس در تنظیمات پنل مدل lmstudio را به qwen2.5-7b-instruct تغییر دهید.

## Session 5 (2026-09-28) — موتورهای هوشمند + امنیت + E2E کامل

### ساخته و تست شد (۸۹/۸۹ تست؛ کامیت 68af7f1 + بعدی)
1. **analytics.py** — معماری کامل Analytics: اسنپ‌شات‌های append-only (هرگز بازنویسی نمی‌شوند؛ متریک‌ها validate می‌شوند)؛ آداپتور ۸ پلتفرم (شامل GSC و هر دو سایت وردپرس) با سلامت صادقانه و BLOCKED_BY_CREDENTIAL؛ job همگام‌سازی؛ رکوردهای عملکرد برای حلقهٔ یادگیری؛ **زمان‌بندی تطبیقی** (BASELINE→DATA_DRIVEN با نمونه/اطمینان/شواهد)؛ **بهینه‌سازی پس از انتشار** (الگوهای واقعی مثل نمایش‌بالا/CTR-پایین → پیشنهاد با تأیید)؛ تشخیص ناهنجاری.
2. **intelligence.py** — **برنامهٔ هفتگی** با شواهد محلی (پروژه‌ها/عملکرد/یافته‌های سئو؛ نمونه روی هر پیشنهاد)؛ **جریان سئو تشخیص→توضیح→پیشنهاد** (proposals با fix مشخص)؛ **Shorts V2** با رتبه‌بندی چندسیگناله و اجبار زاویه‌های متفاوت.
3. **تشخیص واقعی sitemap tehnet.ir**: sitemap.xml → 301 → wp-sitemap.xml → 404 و بدون خط Sitemap در robots.txt — یعنی sitemap وردپرس غیرفعال و سئوپلاگین نصب نیست. crawler حالا ریدایرکت را دنبال می‌کند و تشخیص در پیشنهاد ثبت شده است.
4. **UI**: صفحهٔ Analytics واقعی (وضعیت آداپتورها/زمان‌بندی تطبیقی/پیشنهادها با تأیید/ثبت دستی عملکرد)، برنامهٔ هفته در ایده‌ها، دکمهٔ پیشنهاد سئو، Shorts V2، و **صفحهٔ کامل «اتصال حساب‌ها»** (scope/متغیر/راهنما/تست اتصال واقعی برای ۸ سرویس).
5. **تست‌های امنیت و بازیابی (۱۲ تست جدید)**: hash رمز، bruteforce + قفل، نشست/خروج، SSRF guard، validation آپلود، جعل تأیید با revision قدیمی، restart وسط صف، شکست worker/FFmpeg/LLM، قطع دیسک آرشیو، انتشار تکراری. CSP دست‌نخورده سخت‌گیرانه ماند.
6. **مستندات**: تناقض CONTINUATION_STATUS رفع شد (قابلیت‌های تست‌شده دیگر future-work نیستند)؛ README هم‌راستا شد.
7. **E2E داخلی کامل با اجزای واقعی** (tests/e2e_full.py روی سرور زنده): صدای فارسی واقعی → whisper medium/CUDA → سناریوی AI با هر ۷ مارکر تولید از LM Studio → رسانه → sync → بهبود صوت → تدوین → preview → final تأییدشده → Shorts V2 → مقاله → اسکن سئو → پیشنهاد سئو → dry-run انتشار → Analytics-ready → بهینه‌سازی.

## Commissioning نهایی (۲۰۲۶-۰۹-۲۹) — وضعیت آماده‌به‌کار روزانه

- **FINAL_E2E_VERIFIED: 24/24** (اجرا واقعی با Qwen؛ مرحلهٔ sync با assertion اصلاح‌شده سبز شد — آفست ‎-1.2s/اطمینان ۰.۹۹)
- Regression: ۱۰۹/۱۰۹ سبز (یک اجرا، طبق سیاست)
- Smoke UI روزانه (مرورگر واقعی): **۱۳/۱۳ PASS** — و دو باگ واقعی گرفت و رفع شد: (۱) مرکز اتصال‌ها با شکل جدید {core,optional} خالی می‌ماند (ادغام شد + GA4/Keyword/Gemini اضافه؛ ۱۱ سرویس) (۲) اسکریپت Backup با WAL خام دیتای خالی می‌گرفت (sqlite backup API شد) و Verify چک LM Studio بدون import json خطا می‌داد (رفع شد)
- Backup واقعی گرفته و validate شد (۲۳ جدول + integrity ok؛ fidelity روی DB پر از دادهٔ E2E اثبات شد)؛ بکاپ قبلی بازنویسی نشد
- Restart/Recovery تست شد: kill سخت ← تاریخچهٔ پروژه و کارها سالم برگشت؛ auth endpoint پاسخ صادقانه
- Verify-Installation: **READY** (تمام OK؛ LM Studio/Qwen هم سبز)
- اختیاری‌ها عمداً خاموش ماندند: Ruflo=DISABLED · Screaming Frog=NOT_INSTALLED (fallback داخلی فعال) · SERP=بدون کلید
- مستندات جدید: DAILY-USE.fa.md (راهنمای کوتاه روزانه)، SITEMAP-CHECKLIST.fa.md (چک‌لیست دستی ۵ دقیقه‌ای رفع sitemap)، CREDENTIALS-GUIDE.fa.md (۱۱ سرویس با نام/محل/scope/تست/لغو)؛ .env.example با راهنمای obtain/revoke
- تنها مانع باقی‌مانده: Credentialهای خارجی شما (فهرست در CREDENTIALS-GUIDE)

## وضعیت یکپارچهٔ فعلی (2026-09-28 — پس از سخت‌سازی عملیاتی)

موارد زیر که قبلاً در همین بخش «کارهای بعدی» بودند، اکنون **تکمیل و تست‌شده‌اند** و دیگر future-work نیستند:
Shorts/رندر عمودی، وردپرس‌کانکتور (کشف CMS + آداپتور پیش‌نویس، credential-gated)، اعلان‌ها (محلی کامل + Telegram credential-gated)، Storage Manager + آرشیو My Passport (checksum/تأیید)، احراز هویت (env-based)، Media Sync چند-ترکه، GPU whisper فعال + انتخاب مدل در UI با بنچمارک واقعی فارسی.

### کارهای باقی‌ماندهٔ مهندسی داخلی (بدون credential)
1. معماری کامل Analytics (schema/adapters/sync jobs/snapshots/UI) — حتی بدون OAuth
2. Learning Loop واقعی + Adaptive Scheduling + Post-publish Optimization
3. Content Matrix + Weekly Planner عملیاتی
4. جریان سئو: تشخیص→پیشنهاد→تأیید→اصلاح→اسکن مجدد
5. Smart Shorts V2 (رتبه‌بندی چندزاویه‌ای + تأیید کاندیدا)
6. تست‌های امنیت/شکست-بازیابی/عملکرد

### BLOCKED_BY_CREDENTIAL (تنها این‌ها منتظر کاربرند)
انتشار واقعی شبکه‌های اجتماعی (OAuth)، Analytics واقعی هر پلتفرم (OAuth)، GSC (OAuth readonly)، تولید تصویر Gemini (API key)، پیش‌نویس وردپرس (Application Password)، اعلان Telegram (Bot Token).

## Required Credentials (فقط این‌ها از کاربر)

- OAuth پلتفرم‌ها برای انتشار/Analytics واقعی.
- TELEGRAM_BOT_TOKEN + chat id برای اعلان.
- GOOGLE_AI_API_KEY برای رندر Gemini (thumbnail/carousel/infographic).

## Known Issues / نکته‌ها

- `py -3` و `python` در PATH ویندوز تازه نصب شده‌اند؛ Open-Panel.cmd باید کار کند (تست دستی نشده چون پنل با تست‌ها و سرور آزمایشی پوشش داده شده).
- مدلی که میدل transcribe استفاده می‌کند 'small' است؛ برای فارسی مدل medium/large-v3 کیفیت بهتر می‌دهد (کندتر). پیکربندی مدل هنوز در UI نیست (payload job آن را می‌پذیرد).
- تست مرورگر بخش رسانه به TEHNET_FFMPEG نیاز دارد (در پیام commit قبلی مستند شد؛ در TECHNICAL.md هم هست).
- CSP اجازه style inline نمی‌دهد؛ progress barها از CSSOM استفاده می‌کنند (الگوی موجود را نگه دارید).
