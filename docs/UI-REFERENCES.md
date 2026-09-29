# UI References — منابع طراحی و وضعیت استفاده

این سند طبق سیاست جلسهٔ بازطراحی v2 ثبت شده است. **نکتهٔ کلیدی: هیچ کدی از هیچ مخزنی کپی نشده است** — تمام CSS/HTML این پروژه اصیل و برای همین محصول نوشته شده. این مخازن فقط الگوی بصری/تعاملی الهام‌بخش بوده‌اند (تکنیک‌هایی مثل Glassmorphism و motion که الگوهای عمومی طراحی وب‌اند و مالکیت خاصی ندارند).

| مرجع | لایسنس (به‌هنگام بررسی ۲۰۲۶-۰۹-۲۹) | چه چیزی الهام گرفت | کجا استفاده شد |
|---|---|---|---|
| [nesdesignco/Glassmorphism-Admin-Panel-UI](https://github.com/nesdesignco/Glassmorphism-Admin-Panel-UI) | MIT | لایه‌بندی شیشه‌ای پنل‌ها، نوار کنار نیمه‌شفاف، برجسته‌شدن آیتم فعال | `style.css`: `.card`، `aside`، `nav a.active` |
| [tweeedlex/react-magic-ui](https://github.com/tweeedlex/react-magic-ui) | بررسی مستقیم نشد (ری‌اکت؛ ما React نداریم) | حس «liquid glass» برای کنترل‌های شناور و درخشش نرم دکمهٔ اصلی | `button.primary`، `.brandchip` |
| [Mucrypt/magic-ui](https://github.com/Mucrypt/magic-ui) | MIT | میکرو-تعامل‌های ظریف: hover-lift، progress درخشان، transition مودال | `.stat:hover`، `.progressfill`، `dialog[open]` |
| [opencolin/threejs-dashboard](https://github.com/opencolin/threejs-dashboard) | بررسی مستقیم نشد | ایدهٔ پس‌زمینهٔ اتمسفری عمیق — اما به‌جای Three.js (قانون پرفورمنس: WebGL اختیاری بماند) | `.atmo` با CSS خالص (۳ orb گرادیانی روی transform) |

**قاعدهٔ پایبسته:** اگر در آینده بخواهید کدی از این مخازن بگیرید، اول لایسنس همان نسخه را ببینید و انتساب را همین‌جا ثبت کنید. فعلاً هیچ وابستگی جدیدی به پروژه اضافه نشده (فقط CSS/HTML خودمان — بدون کتابخانهٔ UI، بدون Three.js، بدون تغییر در بسته‌ها).
