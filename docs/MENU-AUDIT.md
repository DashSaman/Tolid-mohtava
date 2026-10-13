# Menu and item audit — 13 October 2026

Version: `1.4.1-interface`. All 22 navigation sections loaded without a page error for Tehran Network and MyTel. All 13 project tabs loaded on the synthetic single-video test project. Browser checks exercised navigation, workspace switching, project selection, job filters, preview controls and rendered-media availability; external publishing actions were not executed.

Fixed: hidden labels/brand selectors below 900 px; missing accessible menu names; the dashboard title shown inside projects; same-route dashboard brand switching; partial job counts/history filters; existing other-brand or archived projects marked as deleted in the global job list.

Counts come from the full job history. The job table displays the newest 500 records matching a status filter. The live failed filter showed all 26 pre-existing failures; they were preserved, not silently cleared. Sixteen pre-existing media records still lack source files. The current recording/render tests were successful, and there were no active jobs at deployment.

Validation: **173 tests passed** in 57.097 seconds; **17 focused readiness tests passed**; JavaScript syntax passed. Deployment followed an integrity-checked backup at `D:\Tolid-Mohtava\backups\20261013-202215` and only restarted the content-panel container.

The delivered edit example is synthetic: 28.767 seconds before editing, 24.483 seconds after removing the static silent tail. It includes audio cleanup, Persian captions and a six-second reviewed settings zoom. The vertical example preserves the tutorial frame. No new paid API/model was installed.

YouTube publication/statistics, Gemini, WordPress and Google data integrations remain dependent on account credentials. Other social channels currently provide manual packages. See the [Persian daily guide](DAILY-READY.fa.md) and [English daily guide](DAILY-READY.en.md).

## نتیجهٔ فارسی

۲۲ منو برای هر دو برند و ۱۳ تب پروژه بدون خطای بارگذاری بررسی شدند. انتخاب برند، نام منوها در عرض کم، عنوان پروژه و نمایش تاریخچهٔ کارها اصلاح شد. ۱۷۳ تست موفق بود. فیلتر «ناموفق» اکنون ۲۶ خطای قبلی را کامل نشان می‌دهد؛ این موارد خطای تازهٔ این تغییر نیستند. نمونهٔ ویدیوییِ تحویل‌شده مصنوعی است و برای مشاهدهٔ نتیجهٔ تدوین ارائه می‌شود.
