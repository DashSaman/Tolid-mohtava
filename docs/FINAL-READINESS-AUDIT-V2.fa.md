# ممیزی آمادگی V2 (پس از Sprint تکمیل) — ۲۰۲۶-۰۹-۲۹

وضعیت هر یافتهٔ V1: FIXED / PARTIAL / BLOCKED_BY_CREDENTIAL / DEFERRED_OPTIONAL (شواهد در JSON)

- **F-001 — FIXED** · require_auth() wired into do_POST before any mutation (media included); 401 on invalid session; login overlay + session-aware boot; test_sprint.AuthEnforcementTests
- **F-002 — IMPLEMENTED / BLOCKED_BY_CREDENTIAL** · providers.py OAuthStore (single-use state=CSRF, expiry) + start/callback for YouTube/Meta(x2)/LinkedIn; UI «اتصال حساب»; no client IDs present
- **F-003 — READY_FOR_CREDENTIAL + hardened** · wordpress_draft: DRAFT-only enforcement, slug/excerpt/categories/tags, retry+backoff, idempotency guard file; test WP idempotency
- **F-004 — IMPLEMENTED / BLOCKED_BY_CREDENTIAL** · analytics.add_ingested raw+normalized; GSC ingest job (real searchAnalytics call, gated); UI «دریافت عملکرد GSC»
- **F-005 — FIXED** · sync results rows show AUTO/MANUAL badge + inline save/clear controls
- **F-006 — WIRED (partial)** · optimize button on analytics; KB/keywords/checktopic/refresh still backend-only => PARTIAL
- **F-007 — PARTIAL (backend unchanged; UI deferred)** · endpoints exist; UI wiring deferred within budget
- **F-008 — PARTIAL** · store+routes exist; UI deferred
- **F-009 — FIXED** · «دریافت دادهٔ GA4» button calls /api/ga4/fetch (gated)
- **F-010 — FIXED(cleanup pending)** · route inert; removal queued next cleanup
- **F-011 — IMPLEMENTED / BLOCKED_BY_CREDENTIAL** · gemini_image real API call + gemini_image_handler job + /api/gemini/generate; renders table versioning
- **F-012 — DEFERRED_OPTIONAL** · unchanged
- **F-013 — DEFERRED_OPTIONAL** · unchanged
- **F-014 — PARTIAL (discovery robust; production unchanged)** · multi-candidate discovery (robots→wp-sitemap→indexes) + candidates recorded; live still 404 until user acts
- **F-015 — DEFERRED_OPTIONAL** · unchanged by policy
- **F-016 — FIXED** · accent tokens desaturated (~25%), glow reduced, layout preserved

شمارش‌ها: تست ۱۱۹/۱۱۹ · E2E ۲۴/۲۴ · Smoke ۱۳/۱۳ · باگ باقی‌مانده: ۰ · فقط منتظر Credential: ۹ سرویس · Deferred: Ruflo/SF/SERP/soak/VM-test
