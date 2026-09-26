# MASTER PROMPT — Tehran Network / MyTel AI Content, SEO & Publishing System

تو Codex هستی و قرار است روی سیستم فعلی من یک سیستم یکپارچه، عملیاتی و تا حد ممکن خودکار برای **تولید محتوا، مدیریت شبکه‌های اجتماعی، SEO، تحلیل داده، بهینه‌سازی و انتشار** بسازی.

این پروژه از قبل شروع شده است. **فرض نکن سیستم خالی است. هیچ ابزار، Agent، Skill، سرویس یا پکیجی را قبل از Audit نصب نکن.**

هدف این Prompt این است که ابتدا وضعیت واقعی سیستم را کشف کنی، سپس فقط Gapهای واقعی را تکمیل کنی و در نهایت سیستم را End-to-End اجرا و تست کنی.

---

# 1. قانون اول: ابتدا Audit، سپس تغییر

قبل از هر نصب یا تغییر:

1. Windows را بررسی کن.
2. WSL/WSL2 و Distributionهای موجود را بررسی کن.
3. Docker و Docker Compose را بررسی کن.
4. Containerها، Volumeها، Networkها و سرویس‌های موجود را Inventory کن.
5. Repositoryها و پروژه‌های موجود را پیدا کن.
6. Agentها، MCPها، Skills، CLIها و Automationهای نصب‌شده را بررسی کن.
7. سرویس‌های SEO موجود را بررسی کن.
8. ابزارهای Social Media موجود را بررسی کن.
9. ابزارهای AI/LLM موجود را بررسی کن.
10. Credentialها و Integrationهای موجود را فقط از نظر وجود بررسی کن؛ Secretها را در Log یا Report چاپ نکن.

خصوصاً بررسی کن آیا موارد زیر از قبل نصب/پیکربندی شده‌اند:

- OpenHands
- LiteLLM
- Ollama
- DispatchSEO
- OpenGSC
- Crawl4AI
- SiteOne
- Lighthouse CI
- changedetection.io
- RSSHub
- Postiz
- Activepieces
- n8n
- PostgreSQL
- Redis
- Dockge
- Cloudflare Tunnel
- Uptime Kuma
- Infisical
- Trivy
- Gitleaks
- Restic
- Telegram Bot integrations
- ابزارهای QA / Testing
- هر SEO Agent دیگری که روی سیستم وجود دارد

ممکن است چند SEO Agent از قبل نصب شده باشند ولی هنوز فعال نشده باشند.

آنها را نیز پیدا و بررسی کن.

## قانون تصمیم‌گیری

همیشه:

**Reuse > Extend > Configure > Install**

یعنی:

اگر ابزار موجود همان کار را انجام می‌دهد، دوباره ابزار مشابه نصب نکن.

اگر بخشی از قابلیت را دارد، ابتدا بررسی کن آیا می‌توان آن را Extend کرد.

فقط وقتی Gap واقعی وجود دارد ابزار جدید اضافه کن.

---

# 2. قبل از Implementation یک Audit Report بساز

گزارش باید مشخص کند:

- چه چیزی نصب است
- چه چیزی فعال است
- چه چیزی نصب ولی غیرفعال است
- چه چیزی ناقص است
- چه چیزی Duplicate است
- چه چیزی واقعاً نیاز داریم
- چه چیزی نیاز به Update دارد
- چه Integrationهایی آماده‌اند
- چه Credentialهایی هنوز باید توسط من وارد شوند
- چه چیزی را پیشنهاد می‌کنی حذف/جایگزین/ادغام کنیم

هیچ Secret، Token، Password یا API Key را نمایش نده.

---

# 3. 17 Skill اصلی

فایل/Repository واقعی Skillها را پیدا و **SKILL.md واقعی هرکدام را بخوان**.

صرفاً از روی نام Skill حدس نزن.

17 Skill عبارت‌اند از:

1. `voice-builder`
2. `newsletter-voice`
3. `profile-optimizer`
4. `post-writer`
5. `graphic-designer`
6. `post-formatter`
7. `reels-scripting`
8. `youtube-thumbnail`
9. `post-scorer`
10. `analytics-dashboard`
11. `pinned-comment`
12. `hook-generator`
13. `content-matrix`
14. `niche-research`
15. `gemini-carousel`
16. `gemini-infographic`
17. `quote-post`

تمام 17 Skill باید بررسی شوند.

اما نصب یا Integration کورکورانه ممنوع است.

برای هر Skill مشخص کن:

- وظیفه واقعی آن چیست
- چه Dependencyهایی دارد
- آیا مشابه آن از قبل روی سیستم وجود دارد
- آیا مستقیماً قابل استفاده است
- آیا باید Adapt شود
- چگونه وارد Workflow اصلی پروژه می‌شود

هیچ‌کدام از تصمیم‌های این Prompt را با Defaultهای Skillها Override نکن.

---

# 4. زبان سیستم

کل محصول User-facing باید فارسی باشد.

شامل:

- Dashboard
- Menu
- Buttons
- Forms
- Reports
- Notifications
- Approval Center
- Analytics
- SEO reports
- Content Editor
- Statusها
- Errorهای قابل نمایش به کاربر

UI باید:

**Persian + RTL**

باشد.

اصطلاحات فنی استاندارد مثل CTR، SEO، Retention، API و نام سرویس‌ها می‌توانند انگلیسی باقی بمانند.

کد، variableها و internal API naming لازم نیست فارسی شوند.

---

# 5. برندها

سیستم حداقل دو Workspace اصلی دارد:

## Tehran Network

برند اصلی:

**Tehran Network / tehnet.ir**

هویت اصلی محتوای فنی است.

## MyTel

برند مستقل:

**MyTel / mytel.one**

تمرکز:

- VoIP
- Issabel
- FreePBX
- SIP
- CRM
- موضوعات مرتبط

یک پنل واحد داشته باش ولی Tehran Network و MyTel Workspaceهای جدا داشته باشند.

Analytics، محتوا، سایت، Social Accountها و History آنها نباید با هم قاطی شوند.

---

# 6. ارتباط Tehran Network و MyTel

اولویت Branding با **Tehran Network** است.

اگر محتوایی مربوط به MyTel باشد:

هم در کانال‌های مناسب Tehran Network و هم در کانال‌های MyTel قابل انتشار باشد.

Approval برای محتوای مشترک یک‌بار انجام شود.

برای ویدیوی مشترک:

- ویدیو با Tehran Network شروع شود.
- لوگوی MyTel دائماً روی تصویر نباشد.
- MyTel در نقاط مناسب به‌عنوان Sponsor نمایش داده شود.
- Sponsor segment برای هر ویدیو متفاوت و Context-aware باشد.
- متن تبلیغاتی ثابت و تکراری نساز.

مثلاً Agent باید بر اساس موضوع تصمیم بگیرد چه نوع اشاره‌ای به MyTel طبیعی‌تر است.

---

# 7. Workflow اصلی تولید محتوا

Workflow مطلوب:

**Idea / Voice → Research → Technical Verification → Script → Approval → Recording → Transcript → Editing → Repurpose → SEO → Publish Approval → Publishing → Analytics → Optimization**

---

# 8. ورودی Voice

من باید بتوانم موضوع را با Voice کاملاً محاوره‌ای و حتی نامرتب توضیح بدهم.

Agent باید:

1. Voice را Transcript کند.
2. منظور و نکات اصلی را استخراج کند.
3. ساختار منطقی ایجاد کند.
4. ادعاهای فنی را بررسی کند.
5. اطلاعات ناقص را مشخص کند.
6. متن را بازنویسی کند.

خروجی باید یک **سناریوی کامل کلمه‌به‌کلمه** باشد.

من قرار است از روی آن بخوانم ولی لحن باید طبیعی و محاوره‌ای باشد، نه رسمی و رباتیک.

---

# 9. Script باید Production-aware باشد

داخل Script Markerهای اجرایی قرار بده، مثل:

- `[FACE CAM]`
- `[SCREEN RECORD]`
- `[B-ROLL]`
- `[GRAPHIC]`
- `[SPONSOR]`
- `[CTA]`
- `[SHORT CANDIDATE]`

این Markerها هم برای من قابل فهم باشند و هم Agent Editing بتواند بعداً آنها را Parse کند.

---

# 10. ضبط واقعی بر Script اولویت دارد

Script فقط راهنماست.

بعد از ضبط، **Transcript واقعی ویدیو Source of Truth است.**

اگر من هنگام ضبط یک قسمت را بهتر، طبیعی‌تر یا کامل‌تر توضیح دادم:

همان نسخه واقعی را نگه دار.

Agent نباید صرفاً برای تطبیق با Script اولیه توضیح بهتر من را حذف کند.

فقط بررسی کند آیا:

- نکته مهمی جا افتاده
- CTA فراموش شده
- Sponsor لازم حذف شده
- خطای فنی ایجاد شده
- بخش ضروری آموزش حذف شده

در این موارد Flag ایجاد کند.

---

# 11. Technical Verification

قبل از تحویل Script نهایی، Agent باید Technical Verification انجام دهد.

مواردی مثل:

- Version نرم‌افزار
- Commandها
- Configuration
- Syntax
- URL
- Documentation
- API behavior
- Feature availability

باید تا حد ممکن Verify شوند.

اولویت منابع:

1. Documentation رسمی
2. GitHub رسمی
3. Repository معتبر
4. Forum تخصصی معتبر
5. منابع Community مثل MikroTik Forum و Stack Overflow در صورت نیاز

اگر منابع اختلاف دارند:

اختلاف را گزارش کن.

منبع رسمی وزن بیشتری دارد.

اگر چیزی Verify نشد:

**Needs Verification**

ثبت کن.

حدس نزن.

---

# 12. Sources / References

هنگام Technical Verification منابع استفاده‌شده را خودکار ذخیره کن.

در انتهای Content/Script بخش:

**منابع و مراجع**

ایجاد شود.

این کار نباید نیازمند جمع‌کردن دستی لینک توسط من باشد.

---

# 13. Pre-Publish Research

قبل از ضبط، برای موضوع تحقیق کن.

بررسی کن:

- عملکرد محتوای قبلی خودمان
- موضوعات موفق
- CTR قبلی
- Retention
- Views
- Engagement
- Search demand
- محتوای رقبا
- زاویه‌های اشباع‌شده
- Content Gapها
- سؤال‌های کاربران
- Search intent

هدف Copy کردن رقبا نیست.

هدف پیدا کردن بهترین Positioning برای محتوای خودمان است.

---

# 14. Hook Generator

برای هر ویدیو چند Hook بساز.

می‌توانند شامل:

- Curiosity
- Problem
- Common mistake
- Contrarian
- Result-driven
- Demo
- Story
- Direct benefit

باشند.

Agent ابتدا گزینه‌ها را تحلیل کند.

خروجی باید شامل:

**Best Pick by Agent**

و همچنین **3 گزینه برتر قابل انتخاب توسط من** باشد.

انتخاب نهایی با من است.

---

# 15. Title + Thumbnail + Hook باید یک Package باشند

Title، Thumbnail و Hook جدا از هم طراحی نشوند.

آنها باید یک Promise مشترک داشته باشند.

برای هر ویدیو چند Package بساز.

مثلاً:

- Curiosity
- Problem/Mistake
- Result/Demo

هر Package شامل:

- Title
- Thumbnail concept
- Hook
- دلیل پیشنهاد

باشد.

---

# 16. Thumbnail

Thumbnail باید بر اساس:

- موضوع
- Audience
- داده کانال
- CTR گذشته
- Competitor research
- Visual patternهای موفق

طراحی شود.

صرفاً Thumbnail زیبا نساز.

هدف افزایش احتمال Click است، بدون Clickbait گمراه‌کننده.

---

# 17. Content Matrix

برای Tehran Network و MyTel Content Pillar و Content Matrix داشته باش.

ایده‌ها فقط تصادفی نباشند.

از ترکیب موارد زیر استفاده کن:

- Brand pillars
- Search demand
- Content gaps
- Audience questions
- Analytics
- Previous performance
- Trends
- Business relevance

ایده‌ها را Prioritize کن.

---

# 18. Repurposing

از ویدیوی اصلی به‌صورت خودکار Candidateهای مناسب برای:

- YouTube Shorts
- Instagram Reels
- Telegram
- Facebook
- LinkedIn
- Website
- سایر فرمت‌های پشتیبانی‌شده

استخراج کن.

Short/Reel فقط Cut تصادفی نباشد.

باید Hook مستقل و Context کافی داشته باشد.

---

# 19. Pinned Comment

برای محتواهایی که پلتفرم اجازه می‌دهد، Pinned Comment پیشنهاد بده.

Pinned Comment ترکیبی از دو هدف باشد:

1. ایجاد Conversation/Engagement
2. هدایت نرم به محتوای اصلی، سرویس یا مرحله بعد

Spammy نباشد.

قبل از انتشار Approval لازم دارد.

---

# 20. انتشار چندپلتفرمی

سیستم باید انتشار را برای موارد زیر تا حد ممکن Automate کند:

- YouTube
- Instagram
- Telegram
- Facebook
- LinkedIn
- Website

پلتفرمی که نتوان برایش Automation قابل اعتماد ایجاد کرد، بی‌دلیل وارد Workflow اصلی نکن.

هدف این نیست که من محتوا را دستی در چند سایت Upload کنم.

Integration اولیه Accountها می‌تواند یک‌بار انجام شود.

بعد از آن Workflow باید از پنل مدیریت شود.

---

# 21. Approval اجباری

در فاز فعلی هیچ محتوای Public بدون Approval من منتشر نشود.

این شامل:

- Video
- Short
- Reel
- Post
- Article
- Thumbnail
- Title change
- SEO-sensitive change
- Pinned comment
- Sponsor content
- Post-publication optimization

است.

بعداً ممکن است برای بعضی Actionهای کم‌ریسک Auto Approval تعریف کنیم.

ولی **فعلاً چنین مجوزی وجود ندارد.**

---

# 22. Approval Center

یک **مرکز تأیید** مرکزی داخل پنل ایجاد کن.

Statusها حداقل:

- منتظر تأیید
- تأیید شد
- رد شد
- نیاز به بررسی

کاربر باید دو امکان داشته باشد:

1. Quick Approval از Approval Center
2. بازکردن Content Detail و Approval از داخل همان صفحه

برای Actionهای مهم جزئیات کامل قابل مشاهده باشد.

---

# 23. Notification

هر چیزی که Approval من لازم دارد، هم‌زمان از این کانال‌ها اطلاع داده شود:

- Dashboard
- Telegram
- Email

Notification باید Deep Link یا مسیر مشخص به Approval مربوطه داشته باشد.

از Notification spam جلوگیری کن و Eventهای مرتبط را در صورت منطقی بودن Group کن.

---

# 24. Analytics

Analytics هر پلتفرم صفحه مستقل داشته باشد.

مثلاً:

- YouTube Analytics
- Instagram Analytics
- Telegram Analytics
- Facebook Analytics
- LinkedIn Analytics
- Website Analytics

داده پلتفرم‌ها را بی‌دلیل مخلوط نکن.

---

# 25. Weekly Analytics

حداقل هفته‌ای یک‌بار داده‌ها را Recalculate کن.

مواردی مثل:

- Views
- Impressions
- CTR
- Retention
- Watch time
- Engagement
- Conversion
- Traffic to main content
- Content performance
- Day/time performance

ذخیره شوند.

History پاک نشود.

هدف این است که بعد از چند ماه Dataset واقعی رفتار Audience خودمان ساخته شود.

---

# 26. Adaptive Scheduling

Schedule ثابت مثل:

"هر سه‌شنبه ساعت 8"

نساز.

Agent باید برای هر Platform بررسی کند Audience واقعی ما:

- چه روزی
- چه ساعتی
- برای چه Content Typeی

بهتر واکنش نشان داده.

Schedule هفته بعد بر اساس داده Recalculate شود.

برای Accountهای جدید یا غیرفعال که Data کافی ندارند:

Baseline منطقی استفاده کن.

Confidence پایین را واضح نشان بده.

بعد از جمع‌شدن Data، تصمیم‌ها را Personalize کن.

---

# 27. Scheduling Metrics

فقط View معیار نباشد.

موارد زیر نیز بررسی شوند:

- CTR
- Retention
- Watch time
- Engagement
- Conversion
- انتقال کاربر از Short/Reel به Main Video
- Sample size

تصمیم مبتنی بر 2 پست را هم‌وزن تصمیم مبتنی بر 50 پست ندان.

---

# 28. Post-Publish Optimization

بعد از انتشار، Performance را Monitor کن.

یک Timeout ثابت مثل 48 ساعت تعریف نکن.

کانال Tehran Network مدتی کم‌فعالیت بوده و ممکن است Data دیرتر جمع شود.

Agent خودش تعیین کند چه زمانی Data برای قضاوت کافی است.

ممکن است:

- 48 ساعت
- 72 ساعت
- بیشتر

نیاز باشد.

تصمیم بر اساس Data Sufficiency باشد، نه Timer ثابت.

---

# 29. Title/Thumbnail Optimization

اگر Data کافی شد و Performance ضعیف بود:

Agent می‌تواند پیشنهاد دهد:

- Title جدید
- Thumbnail جدید
- Metadata adjustment
- Hook/positioning insight برای محتوای بعدی

اما خودش تغییر ندهد.

Proposal → Notification → Approval → Apply

---

# 30. SEO سایت

SEO بخشی از Core System است، نه Add-on.

هر مطلبی که برای Website ساخته می‌شود باید قبل از انتشار SEO Review شود.

بررسی حداقل شامل:

- Search intent
- Primary keyword
- Secondary keywords
- Title
- Meta description
- Heading structure
- Internal linking
- External references
- URL/slug
- Image alt text
- Schema opportunity
- Canonical
- Indexability
- Duplicate content
- Content quality
- Technical SEO concerns

باشد.

---

# 31. SEO Agentهای موجود را اول بررسی کن

روی سیستم از قبل چند Agent/Tool مربوط به SEO وجود دارد.

ممکن است هنوز فعال نشده باشند.

آنها را پیدا کن.

خصوصاً:

- DispatchSEO
- OpenGSC
- Crawl4AI
- SiteOne
- Lighthouse CI

و هر ابزار SEO دیگری که واقعاً پیدا می‌کنی.

قبل از نصب ابزار SEO جدید تعیین کن:

- چه Capability داریم
- چه Capability نداریم
- چه چیزهایی Overlap دارند

بعد Architecture نهایی SEO را بساز.

---

# 32. SEO کل سایت

SEO فقط برای Article جدید نیست.

Agentها باید بتوانند سایت را نیز Audit کنند.

شامل:

- Technical SEO
- Crawl issues
- Broken links
- Redirects
- Indexability
- Sitemap
- robots.txt
- Canonical
- Metadata
- Core Web Vitals در صورت امکان
- Performance
- Internal linking
- Orphan pages
- Duplicate content
- Structured data
- Content gaps
- Search Console data
- Ranking/query opportunities

---

# 33. SEO Automation

سیستم می‌تواند:

- Audit
- Detect
- Analyze
- Recommend
- Prepare fix

را خودکار انجام دهد.

اما تغییرات مهم سایت ابتدا Approval بخواهند.

هیچ تضمین رتبه Google یا Top-10 نده.

هدف Data-driven continuous improvement است.

---

# 34. Website Content

محتوای Website نباید صرفاً Transcript ویدیو Copy/Paste شود.

Agent باید آن را به Article مناسب Web تبدیل کند.

اما معنی و ادعاهای فنی نباید تحریف شوند.

برای محتوای مرتبط MyTel:

نسخه مناسب mytel.one ایجاد شود.

برای Tehran Network:

نسخه مناسب tehnet.ir ایجاد شود.

از Duplicate Content غیرضروری بین دو سایت جلوگیری کن.

---

# 35. Post Scoring

قبل از انتشار Content Quality Score ایجاد کن.

Score باید Explainable باشد.

مثلاً:

- Hook
- Clarity
- Technical confidence
- SEO
- CTA
- Brand fit
- Platform fit
- Readability
- Thumbnail/title consistency

Score نباید به‌تنهایی Publication را تعیین کند.

من Approval نهایی را می‌دهم.

---

# 36. Dashboard اصلی

Dashboard فارسی حداقل باید نمای کلی این موارد را بدهد:

- محتوای در حال تولید
- منتظر تأیید
- Scheduled
- Published
- Failed jobs
- SEO alerts
- Analytics alerts
- Optimization suggestions
- Tehran Network
- MyTel
- System health

---

# 37. Background Automation

تا حد ممکن کارها Event-driven یا Scheduled باشند.

مثل:

- Weekly analytics
- SEO crawling
- Performance monitoring
- Content performance evaluation
- Scheduling recommendation
- Broken-link checks
- Search Console sync
- Social analytics sync

Failureها Silent نباشند.

Log + Notification ایجاد شود.

---

# 38. Reliability

هر Workflow مهم باید:

- Retry policy
- timeout
- idempotency
- logging
- failure state
- recovery path

داشته باشد.

Duplicate publish به دلیل Retry نباید رخ دهد.

---

# 39. Security

هیچ API Key، Password یا Token را:

- hard-code
- commit
- print
- expose in UI

نکن.

Secret management موجود را Audit کن.

اگر Infisical یا راهکار مشابه از قبل فعال است، ابتدا از همان استفاده کن.

Principle of least privilege را رعایت کن.

---

# 40. Non-destructive implementation

سیستم موجود Production/Development ممکن است سرویس‌های دیگری داشته باشد.

هیچ Container، Volume، Database، Repository یا Config را بدون شناخت حذف نکن.

قبل از Migration یا تغییر خطرناک:

- backup
- rollback path
- verification

لازم است.

---

# 41. UI/UX

هدف ساخت پنلی است که من مجبور نباشم برای کار روزانه Terminal باز کنم.

پنل باید فارسی، RTL و ساده باشد.

صفحات اصلی پیشنهادی:

- داشبورد
- تهران نتورک
- MyTel
- محتوا
- سناریوها
- تقویم انتشار
- مرکز تأیید
- Analytics
- SEO
- منابع
- اعلان‌ها
- تنظیمات
- وضعیت Agentها و Automationها

هر Platform در Analytics صفحه مستقل داشته باشد.

---

# 42. Human-in-the-loop

اصل معماری:

**Automation does the work; Human controls important decisions.**

Agentها باید کار تکراری را انجام دهند.

من نباید برای هر مرحله Micro-manage کنم.

اما تصمیم Public/Brand-sensitive فعلاً با من است.

---

# 43. Logging تصمیم‌ها

برای هر Content Item History نگه دار:

- ایده اولیه
- Research
- Script versions
- Technical verification
- Sources
- Approval
- Recording
- Transcript
- Edits
- Generated derivatives
- Publication
- Analytics
- Optimization proposals
- Changes approved/rejected

تا بعداً بفهمیم چه چیزی باعث موفقیت یا شکست محتوا شده.

---

# 44. Learning Loop

سیستم باید به مرور از Data خودمان استفاده کند.

Loop:

**Create → Publish → Measure → Learn → Adjust**

یادگیری باید در موارد زیر اثر بگذارد:

- Topic selection
- Hook
- Title
- Thumbnail
- Posting time
- Content length
- Format
- CTA
- Repurposing
- Sponsor placement

---

# 45. ابتدا چیزی نساز که قبلاً داریم

این نکته حیاتی است.

ممکن است سیستم من همین حالا تعداد زیادی Agent، Skill و سرویس داشته باشد.

قبل از Implementation واقعی:

**Discovery کامل انجام بده.**

برای هر نیاز جدول Capability Matrix بساز:

| Capability | Existing Tool | Status | Gap | Action |
|---|---|---|---|---|

Action فقط یکی از این‌ها باشد:

- REUSE
- CONFIGURE
- EXTEND
- INSTALL
- REPLACE
- REMOVE-LATER

هیچ چیز را فقط به دلیل اینکه خودت Tool دیگری را ترجیح می‌دهی جایگزین نکن.

---

# 46. نحوه اجرای پروژه

کار را مرحله‌ای انجام بده.

## Phase 0 — Discovery

فقط Read-only Audit.

هیچ نصب و تغییر Production انجام نده.

## Phase 1 — Architecture

بر اساس Audit معماری واقعی را طراحی کن.

نه معماری فرضی.

## Phase 2 — Gap Analysis

مشخص کن چه چیزهایی کم است.

## Phase 3 — Foundation

Database، Queue، API، Auth، Secret handling و Integrationهای لازم را تکمیل کن.

## Phase 4 — Content Pipeline

Voice → Research → Script → Approval → Recording workflow.

## Phase 5 — Editing / Repurpose

Transcript و derivative content.

## Phase 6 — Publishing

Social + Website integrations.

## Phase 7 — SEO

Content SEO + Site SEO.

## Phase 8 — Analytics

Per-platform Analytics + Weekly analysis.

## Phase 9 — Optimization

Adaptive schedule + post-publish optimization.

## Phase 10 — Hardening

Tests، monitoring، backups، security، failure recovery.

---

# 47. بعد از هر Phase

قبل از اعلام Completion:

- Test کن.
- Evidence ارائه بده.
- مشخص کن چه چیزی واقعاً کار می‌کند.
- Failureها را مخفی نکن.
- TODO واقعی را بنویس.

عبارت «انجام شد» فقط وقتی استفاده شود که Test آن را تأیید کرده باشد.

---

# 48. Documentation

تمام تصمیم‌ها، نصب‌ها، تغییرات، Errorها و نتیجه Testها را Document کن.

اگر Repository مستندسازی موجود مثل:

`DashSaman/-SEO`

روی سیستم وجود دارد، ابتدا آن را بررسی کن و Documentation را با ساختار موجود هماهنگ کن.

اطلاعات حساس وارد Git نشوند.

---

# 49. Agent Checklist

یک Checklist دائمی برای پروژه بساز.

هر Task وضعیت داشته باشد:

- TODO
- IN PROGRESS
- BLOCKED
- VERIFIED

هر VERIFIED باید Evidence داشته باشد.

---

# 50. چیزی را از من دوباره نپرس که قابل کشف است

اگر می‌توانی پاسخ را از:

- filesystem
- Docker
- WSL
- Git
- config
- documentation
- API
- installed agents
- repository

پیدا کنی، از من سؤال نکن.

اول خودت بررسی کن.

فقط زمانی سؤال کن که:

- Credential لازم است
- تصمیم Business لازم است
- Approval لازم است
- اطلاعات از سیستم قابل کشف نیست

---

# 51. Credentialها

اگر Integration به Login/API Key نیاز دارد:

Implementation را تا مرحله‌ای که بدون Secret ممکن است جلو ببر.

سپس دقیقاً بگو:

- چه Credentialی لازم است
- برای کدام Service
- چه Scope حداقلی لازم است
- کجا باید وارد شود

Secret را از من داخل Chat یا Source Code درخواست نکن اگر روش امن‌تری وجود دارد.

---

# 52. معیار موفقیت نهایی

سیستم نهایی باید تا حد ممکن این تجربه را ایجاد کند:

من موضوع را با Voice توضیح می‌دهم.

سیستم Research و Technical Verification می‌کند.

سناریوی کامل فارسی و محاوره‌ای می‌سازد.

Hook، Title و Thumbnail پیشنهاد می‌دهد.

من تأیید می‌کنم و ویدیو را ضبط می‌کنم.

سیستم فایل واقعی را Transcript می‌کند و توضیح واقعی من را Source of Truth قرار می‌دهد.

ویدیو و محتوای جانبی را آماده می‌کند.

نسخه‌های مناسب هر Platform را می‌سازد.

Article SEO شده می‌سازد.

Pinned Comment آماده می‌کند.

تمام خروجی‌ها در Approval Center قرار می‌گیرند.

من یک‌بار بررسی/تأیید می‌کنم.

سیستم در Platformهای مناسب منتشر می‌کند.

Analytics را جمع می‌کند.

هر هفته عملکرد را تحلیل می‌کند.

زمان انتشار را بر اساس Data واقعی Audience تنظیم می‌کند.

SEO سایت را مداوم بررسی می‌کند.

اگر Title/Thumbnail یا بخش دیگری نیاز به Optimization داشت، پیشنهاد می‌دهد.

هیچ تغییر مهمی بدون تأیید من انجام نمی‌دهد.

و سیستم از نتایج گذشته برای تصمیم‌های بعدی یاد می‌گیرد.

---

# 53. دستور شروع برای Codex

**الان Implementation را با نصب ابزار جدید شروع نکن.**

ابتدا فقط **Phase 0 — Read-only Discovery & Audit** را انجام بده.

تمام سیستم موجود، WSL، Docker، Repositoryها، Agentها، 17 Skill، SEO Agentها، Automationها و Integrationها را بررسی کن.

سپس این خروجی‌ها را بده:

1. **System Inventory**
2. **Existing Agents & Tools**
3. **17 Skills Audit**
4. **SEO Stack Audit**
5. **Social/Publishing Stack Audit**
6. **AI/LLM Stack Audit**
7. **Capability Matrix**
8. **Duplicate/Overlap Analysis**
9. **Gap Analysis**
10. **Recommended Architecture based on what actually exists**
11. **Implementation Plan**
12. **Risks / Blockers**
13. **Credentials or approvals eventually required**

در Phase 0 هیچ سرویس موجودی را حذف، Upgrade، Restart یا Reconfigure نکن مگر اینکه صرفاً برای Read-only inspection ضروری باشد و هیچ Stateی را تغییر ندهد.

بعد از Audit، قبل از تغییرات پرریسک یا معماری‌ای که نیاز به تصمیم من دارد، نتیجه را ارائه کن.

**از سیستم واقعی به‌عنوان Source of Truth استفاده کن، نه فرضیات این Prompt.**