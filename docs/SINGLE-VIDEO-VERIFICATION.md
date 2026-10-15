# Single-video verification — 13 October 2026

The owner-approved local workflow is deployed on this installation at http://127.0.0.1:18767. Current source branch: `ready/2026-10-13`, version `1.4.0-single-video`.

- Full suite: **172 tests passed** in 55.064 seconds. Fresh focused editing suite: **23 passed**. Documentation check: **174 relative links and 4 historical screenshots passed**. JavaScript syntax check passed.
- Actual Docker workflow used a synthetic merged network-settings video with Persian speech and a static silent tail. Source duration: 28.767 seconds; reviewed cut: 23.491–27.775; final duration: 24.483 seconds.
- Existing Whisper **medium**, **CUDA**, real word timestamps; existing local Ollama **qwen3.5:4b** performed text and image analysis. A valid settings region produced a **1.266×**, six-second zoom with a Persian review label.
- FFmpeg **NVENC** produced preview/final MP4 with audio, burned-in Persian captions and downloadable SRT/VTT/ASS. A real **1080×1920** Short inherited the edited final. Before/after source SHA256 matched.
- Final submission with a client-supplied approval flag still waited for explicit approval. Isolated checks rejected stale cuts before registering a final, rebuilt previews without repeating AI, required new approval and accepted rejection without rendering.
- Twelve fractional cuts were verified with visible/audible markers throughout the output; drift stayed within the test's 60 ms bound. Unsafe command/negation changes, duplicate cycles and retained references inside cuts are rejected. Even tiny sampled cursor activity protects a silent instructional window.
- Real-browser checks covered preview controls, subtitle links, approval preview, visible feedback for changed options, zoom review and rapid navigation after login. Duplicate login overlays and delayed-page overwrites were corrected.

These checks use synthetic fixtures, not the owner's actual training footage. Caption accuracy still requires review. Real external publishing/analytics were not exercised: YouTube OAuth and other provider credentials are not connected. Other social channels currently offer manual publication packages; full multicamera composition and detailed YouTube retention/watch-time analytics remain outside this release.

## نتیجهٔ فارسی

مسیر تدوین یک ویدیوی دارای تصویر و صدا، روی نصب محلی آزمایش و فعال شد: متن فارسی، برش محافظه‌کارانه، بهبود صدا، زیرنویس، زوم قابل حذف، پیش‌نمایش، تأیید طرح، رندر نهایی و Short. RAW ثابت ماند. ۱۷۲ تست و بررسی مرورگر موفق بود. نمونهٔ آزمون مصنوعی است؛ ضبط واقعی کانال هنوز برای ارزیابی کیفیت در اختیار این آزمون نبوده است. نیاز اتصال حساب‌ها در [راهنمای روزانه](DAILY-READY.fa.md) توضیح داده شده است.
