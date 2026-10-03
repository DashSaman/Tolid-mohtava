# DEFECT BACKLOG — FULL DISCOVERY AUDIT (2026-10-03)

> فقط کشف/طبقه‌بندی — هیچ رفع‌ی در این اجرا انجام نشد. رانتایم: reconcile-main @ 31e3259 (کد=ایمیج=کانتینر هم‌تراز).

| ID | Priority | Area | Title | Reproduction | Expected | Actual | Evidence | Root Cause Known? | Current/Historical | Blocks Production? | Suggested Fix Scope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BUG-001 | P1 | AI/Jobs | 6 of 7 AI handlers crash on top-level JSON-array model output | model returns ['a','b'] (string-array) via extract_json -> handler does data.get() | graceful parse_error + strict retry (as hooks fix does) | AttributeError 'list' object has no attribute 'get' — raw traceback in UI | static audit: research/techverif/packages/social/article/pinned UNGUARDED; 4 live hooks crashes in Jobs UI; hooks fixed in 39d7900, other 6 handlers not | YES | CURRENT | YES | apply 39d7900 pattern centrally in _llm_json return + per-handler tolerance |
| UX-001 | P2 | Jobs | Raw technical error strings shown to user | open Jobs page — any failed AI job | meaningful Persian primary message; details expandable | "'list' object has no attribute 'get'", "<urlopen error [Errno 101]...>" rendered inline | screenshot docs/defects/screenshots/UX-jobs-raw-errors.png | YES | CURRENT | no | presentation-layer sanitize in app.js job rows |
| UX-002 | P2 | Jobs/Language | snake_case job kinds as titles (seo_scan, shorts_v2, ...) | Jobs page | Persian display names for every kind | 6 kinds missing from jobKinds map | live #view scan; DB kinds vs jobKinds diff: enhance_audio, optimize_content, seo_proposals, seo_scan, shorts_v2, sync_content | YES | CURRENT | no | add 6 labels |
| UX-003 | P2 | Jobs | No historical/current distinction, no failed-only filter | Jobs default view | filters + context for old failures | flat list; 12 red LM-off-era rows dominate | live check: no filter, no historical labels | YES | CURRENT | no | filter chips + softened historical rows |
| OPS-001 | P2 | AI/Dependency | Dependency-offline errors embed raw urlopen text | stop LM server -> research job | BLOCKED_BY_DEPENDENCY + Persian reason only | message contains <urlopen error [Errno 101] Network is unreachable> | live LM-off test (server safely stopped/restarted) | YES | CURRENT | no | strip errno details |
| OPS-002 | P2 | AI/Dependency | No pre-flight dependency readiness check before AI enqueue | enqueue AI job while LM down | pre-check or immediate blocked status | queues, runs, fails at request time (looks like crash) | observed; no probe in enqueue path | YES | CURRENT | no | cheap TCP probe on enqueue |
| DATA-001 | P2 | Data | 29 orphan jobs reference deleted content | normal project delete keeps jobs (by design) but no orphan marker | linkable/orphan-marked history | 29 jobs -> missing content ids | container-side DB audit | YES | CURRENT | no | mark/filter orphans in UI |
| DATA-002 | P2 | Data | 12 media rows with missing files | container-side audit | row+file lifecycle consistent | 12 rows path-not-exists | DB audit | YES | CURRENT | no | reconcile or filter |
| OPS-003 | P3 | Thumbnails | Thumbs page broken-image 404s for orphan media rows | open Thumbs | placeholder or exclusion | 5 console+HTTP 404s /api/media/file?id=... | page-tour thumbs errs:5 http:5 | YES | CURRENT | no | placeholder or filter |
| UX-004 | P3 | Notifications | Raw traceback text on Notifications page | open notifications | clean Persian list | RAW-TRACE match | page-tour flag | YES | CURRENT | no | sanitize bodies |
| UX-005 | P3 | Services | English raw strings on Health page | open خدمات و سلامت | Persian | RAW-EN flag | page-tour flag | YES | CURRENT | no | translate |
| OPS-004 | P3 | SEO | seo_scan accepts invalid/unreachable URL and completes | POST /api/seo/scan url='not-a-url' / unreachable host | validation + honest failure | queued with payload.site=null then completed | live API test | YES | CURRENT | no | validate + pass through |
| OPS-005 | P3 | Runbook | Stale remote URL (dead v4 hairpin IP) | docs/OPERATOR-RUNBOOK.fa.md line 10 | current v6 sidecar URL | http://100.118.10.107:8766 | doc grep | YES | CURRENT | no | update line |
| DOC-001 | P3 | Docs | QUICKSTART/INSTALLATION/RUNBOOK still lead with native panel | grep Open-Panel.cmd | docker-first, native=rollback | 3 docs native-first | grep list | YES | CURRENT | no | rewrite start sections |
| BUG-002 | P3 | Jobs/Retry | Retry of LM-off historical job re-fails identically | retry 5da183c9 | dependency re-check + clear blocked state | re-failed; row updated in place | live retry test | YES | CURRENT | no | combine with OPS-002 |
| HIST-001 | historical | AI | 12 generate_* LM-off failures (14:49-15:41) | n/a | n/a | n/a | jobs audit | YES | HISTORICAL | no | none (context for UX-003) |
| HIST-002 | historical | AI | 4 generate_hooks array crashes | n/a | n/a | n/a | fixed in 39d7900; live-verified completed/6 | YES | HISTORICAL | no | none |
| HIST-003 | historical | Whisper | 1 empty-transcript refusal (2026-09-29) | n/a | n/a | n/a | jobs audit | YES | HISTORICAL | no | none |

**شمارش:** P0=0 · P1=1 · P2=7 · P3=7 · تاریخی=3 · مجموع=18

**بلاکرهای تولید فعلی:** فقط BUG-001 (کرش ۶ هندلر AI روی آرایهٔ JSON) — بقیه UX/Ops/Docs.
