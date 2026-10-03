# راهنمای نصب (INSTALLATION فارسی)

برچسب‌ها: **[الزامی]** **[اختیاری]** **[نیازمند حساب خارجی]**

## ویندوز — مسیر اصلی
1. **[الزامی]** Python 3.12: `winget install Python.Python.3.12`
2. **[الزامی]** FFmpeg: `winget install Gyan.FFmpeg` (پنل مسیر winget را خودش پیدا می‌کند؛ یا `TEHNET_FFMPEG` بدهید)
3. **[الزامی]** مخزن: `git clone https://github.com/DashSaman/Tolid-mohtava.git`
4. **[الزامی]** بوت‌استرپ: `powershell -ExecutionPolicy Bypass -File setup\Setup-TolidMohtava.ps1` — Python/FFmpeg غایب را نصب، پوشه‌ها را می‌سازد، `.env` نمونه می‌سازد؛ idempotent.
5. **[الزامی]** مدل گفتار: پیش‌فرض `medium` (بنچمارک واقعی فارسی: هم‌پوشانی ~۷۶٪، RTF 0.11 روی CUDA). تغییر از تنظیمات پنل.
6. **[اختیاری but توصیه‌شده]** CUDA برای whisper: `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` — بدون آن، خودکار CPU.
7. **[الزامی برای تولید محتوا]** LM Studio + مدل:
   - `lms server start`
   - `lms load qwen2.5-7b-instruct --gpu max`  (پیش‌فرض؛ fallback: `meta-llama-3-8b-instruct`)
   - دانلود مدل: `lms get "qwen2.5-7b-instruct@q4_k_m"`
8. **[اختیاری]** تست مرورگر پنل: `npm install --no-save playwright` سپس `node tests/ui-flow.cjs` (Chrome نصب‌شده لازم دارد)

## GPU/CUDA
- whisper: CUDA float16 در صورت وجود درایور NVIDIA؛ در صورت خطای DLL، خودکار CPU int8.
- مدل زبانی: از طریق LM Studio (بک‌اند Vulkan روی این درایورها پایدارتر است — پنل هیچ بک‌اندی را قفل نمی‌کند).
- رندر: NVENC در صورت پشتیبانی ffmpeg؛ وگرنه libx264 با نمایش صادقانه «رندر با CPU».

## دسترسی از موبایل (اختیاری)
- [نیازمند تصمیم شما] Tailscale را روی کامپیوتر و گوشی نصب کنید و از آدرس Tailscale باز کنید.
- قبل از آن، احراز هویت پنل را فعال کنید: `ADMIN_USER` و `ADMIN_PASSWORD` در environment.
- **هرگز پورت 8766 را روی روتر باز نکنید.**

## ابزارهای اختیاری
- **[نیازمند حساب خارجی]** WordPress/Telegram/YouTube/…: جدول [.env.example](../.env.example) و صفحهٔ «اتصال حساب‌ها» در پنل.
- **[اختیاری]** Ruflo (هم‌اردازی): `RUFLO_ENDPOINT` را تنظیم کنید؛ بدون آن پنل کامل کار می‌کند.
- **[اختیاری]** Screaming Frog: نصب لایسنس‌دار + `SCREAMING_FROG_PATH`؛ بدون آن خزندهٔ داخلی (تست‌شده، محدود و مؤدب) استفاده می‌شود.

## WSL؟
اجزای اصلی Native ویندوزی‌اند (GPU/رسانه قابل اطمینان‌تر). سرویس WSL لازم نیست.
