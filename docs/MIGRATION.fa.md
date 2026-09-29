# انتقال به کامپیوتر جدید (MIGRATION فارسی)

سناریو: «یک کامپیوتر دیگر خریدم؛ کل پروژه را همان‌جا می‌خواهم.»

## روی سیستم قدیمی
```powershell
powershell -ExecutionPolicy Bypass -File setup\Backup-TolidMohtava.ps1 -IncludeMedia -Out D:\tolid-backup
# بدون -IncludeMedia فقط دیتابیس + ایندکس رسانه (سبک؛ RAW بعداً از My Passport هم قابل برگرداندن است)
```
خروجی: پوشهٔ `tolid-<زمان>` شامل `content.sqlite` (همهٔ پروژه‌ها/تأییدها/کارها/تحلیل‌ها)، `media-index.json`، در صورت درخواست پوشهٔ `media` (RAW)، و `ENVIRONMENT.json`.
**نکته:** `.env` اگر داشتید داخل بکاپ با پسوند امن کپی می‌شود؛ آن را جداگانه و امن منتقل کنید، نه در Git.

## روی سیستم جدید
```powershell
git clone https://github.com/DashSaman/Tolid-mohtava.git
cd Tolid-mohtava
powershell -ExecutionPolicy Bypass -File setup\Setup-TolidMohtava.ps1
powershell -ExecutionPolicy Bypass -File setup\Restore-TolidMohtava.ps1 -From D:\tolid-backup\tolid-... -WithMedia
powershell -ExecutionPolicy Bypass -File setup\Verify-Installation.ps1
```
`Restore` اگر دیتابیس موجود باشد، اول آن را با مهر زمانی کنار می‌گذارد — **هرگز بی‌اجازه بازنویسی نمی‌کند.**

## بعد از Restore
1. **رمزها/کلیدها را خودتان دوباره وارد کنید** (`[Environment]::SetEnvironmentVariable(...,'User')` یا `.env`) — از Git/بکاپ منتقل نمی‌شوند.
2. LM Studio: نصب + `lms get "qwen2.5-7b-instruct@q4_k_m"` + `lms load qwen2.5-7b-instruct --gpu max`.
3. مسیرها: اگر درایوها فرق دارد، `TEHNET_PANEL_DB` و `TEHNET_FFMPEG` از `.env.example` تنظیم کنید.
4. صحت رسانه: صفحهٔ «فضای ذخیره‌سازی» → وضعیت checksum فایل‌ها؛ My Passport را وصل کنید و مسیر آرشیو را همان‌جا ببینید.
5. تست پایانی: `python -m unittest discover -s tests` (حداقل store/jobs سبز) + باز کردن پنل و دیدن پروژه‌ها.

## چیزهایی که منتقل نمی‌شوند (عمداً)
- Secretها (امنیت شما) — دوباره وارد کنید.
- مدل‌های LM Studio (بزرگ) — دستور دانلود بالا.
- فایل‌های temp کش — نیازی نیست.
