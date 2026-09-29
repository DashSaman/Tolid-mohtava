# شروع سریع (QUICKSTART فارسی)

## حداقل سخت‌افزار
- ویندوز ۱۰/۱۱، ۱۶GB RAM، ۲۰GB فضای آزاد. (بدون GPU هم کار می‌کند؛ فقط کندتر.)

## پیشنهادی (تست‌شدهٔ همین سیستم)
- RTX 3070 Laptop 8GB، 32GB RAM — تبدیل گفتار CUDA، رندر NVENC، مدل 7B روی GPU.

## ۵ قدم تا پنل آماده
```powershell
git clone https://github.com/DashSaman/Tolid-mohtava.git
cd Tolid-mohtava
powershell -ExecutionPolicy Bypass -File setup\Setup-TolidMohtava.ps1   # فقط بار اول؛ دوباره اجرا بی‌خطر
powershell -ExecutionPolicy Bypass -File setup\Verify-Installation.ps1  # باید READY یا READY_WITH_OPTIONAL_WARNINGS بدهد
.\Open-Panel.cmd                                                        # مرورگر باز می‌شود: http://127.0.0.1:8766
```

## اولین پروژهٔ محتوا
1. «+ محتوای جدید» → برند → **ضبط صدا** یا متن → عنوان → ساخت.
2. تب **هوش مصنوعی** ← «خط تولید کامل» ← صبر تا کامل شود.
3. سناریو را ببینید؛ اگر خوب بود «ثبت به‌عنوان سناریوی پروژه» و سپس «تأیید سناریو برای ضبط».
4. بعد از ضبط: تب **رسانه** ← آپلود فیس‌کم/صفحه ← همگام‌سازی ← تحلیل تدوین ← بازگردانی هر برش ناخواسته ← **ساخت Preview** ← تأیید نهایی.

## خاموش/روشن
- پنل: پنجرهٔ server را ببندید؛ دوباره `Open-Panel.cmd`. تاریخچه و صف باقی می‌ماند.

## پشتیبان سریع
```powershell
powershell -ExecutionPolicy Bypass -File setup\Backup-TolidMohtava.ps1
```

## Health Check
صفحهٔ **سلامت سیستم** در پنل، یا `setup\Verify-Installation.ps1`.
