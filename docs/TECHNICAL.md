# Technical reference / راهنمای فنی

## Runtime

Python 3.10+, standard library only. `outputs/panel/server.py` uses ThreadingHTTPServer, binds only to `127.0.0.1`, and opens a local SQLite database through `store.py`. `registry.py` checks the current discovery paths against the pinned SKILL.md hashes. There is no model client, job queue, publication adapter or analytics sync.

| Variable | Default | Meaning |
|---|---|---|
| TEHNET_PANEL_PORT | 8766 | Loopback HTTP port |
| TEHNET_PANEL_DB | outputs/panel/data/content.sqlite | Database location |
| CODEX_HOME | ~/.codex | Global skill discovery root |
| PLAYWRIGHT_MODULE | playwright | Optional browser-test package path |
| PYTHON | python | Python executable for browser tests |

## Files and responsibilities

| File | Responsibility |
|---|---|
| store.py | Transactions, validation, version conflicts, independent approvals, history and export |
| server.py | HTTP allowlist, JSON endpoints, Host/Origin/token checks and CSP |
| registry.py | Read-only detection of project-local or global skill files |
| index.html | Persian semantic HTML, forms and dialogs |
| style.css | RTL, desktop/mobile layout, keyboard focus |
| app.js | Navigation, input handling, safe rendering and prompt composition |
| skills.json | Reviewed skill names, dependencies, mappings and pinned hashes |
| backup.py | SQLite backup API for the default database |
| scripts/install_skills.py | Offline checksum-verified copy; preserve existing destinations |
| scripts/start_panel.py | Detect running panel, otherwise start it; optional browser opening |

## HTTP API

All URLs below are local. There is no permissive CORS response. Every request requires the correct Host. Mutation requires `Content-Type: application/json`, an allowed Origin when present, and `X-Panel-Token` from `/api/session`. Never publish this session token.

| Method / route | Purpose |
|---|---|
| GET /api/session | Application marker and per-process mutation token |
| GET /api/skills | 17 definitions plus actual local installation status/path |
| GET /api/items?brand=tehran-network | Filtered content list; also accepts mytel |
| GET /api/history?id=ID | Full snapshots for one record |
| GET /api/export?brand=mytel | Schema 1 JSON containing records and history |
| GET /api/profile?brand=mytel | Canonical about-me, voice and brand-kit files |
| GET /api/policy | Shared Persian policy |
| POST /api/items | Create, or update with id and matching revision |
| POST /api/decide | id, revision, gate (script/publish), status |
| GET /audit, /guide | Static Persian documentation |

Content fields: `title`, `brands`, `body`, `transcript`, `sources`, `notes`, `platform`, `stage`, `due`. Server fields: `id`, `revision`, `created`, `updated`, `script_status`, `publish_status`. Valid decisions: `pending`, `approved`, `rejected`, `review`. The server rejects empty approved body, missing title, invalid brands, oversized fields and stale revisions. Every edit resets approvals. Same-state decisions are idempotent. Publication is not a state this API can perform.

## Data and security boundaries

SQLite tables: `content` stores current JSON records; `events` stores complete historical snapshots. Transactions use `BEGIN IMMEDIATE` for writes. Connections are explicitly closed for Windows file safety. This is not an append-only security audit log against a local administrator, and not a multi-user authorization system. Brand filtering is workflow separation, not separate user permissions.

Only explicit static files are HTTP-served. Database files, Python source, backups and arbitrary paths are not exposed. User content is escaped before HTML rendering. There is a 1.5 MB request limit and 200,000-character text-field limit. A browser session holds the mutation token in memory. The app currently suppresses routine HTTP access logs; it records content decisions, not a full background-job error ledger.

Default backup: `python outputs/panel/backup.py`. For a custom `TEHNET_PANEL_DB`, use SQLite backup against that explicit file; the shipped backup helper deliberately targets only the default path. Restore with this panel stopped and the previous DB preserved. JSON export is inspectable but has no UI import path yet.

## Tests

`python -m unittest discover -s tests -v` runs storage, offline installation and isolated HTTP tests. HTTP tests use an ephemeral loopback port and a temporary database, not the user's running panel. `python tests/check_docs.py` checks local documentation links and expected image assets. `node tests/ui-flow.cjs` uses existing Chrome/Playwright and its own isolated test server.

The browser test checks real create/edit controls, brand isolation, escaping, independent approvals, invalidation, search, JSON history export and persistence across restart. Runtime screenshots are generated separately with clearly labelled synthetic test content.

## حدود نسخه

موعد محتوا صرفاً یک رشته تاریخ برای نمایش است؛ زمان‌بندی تطبیقی یا job زمان‌دار اجرا نمی‌شود. منابع فعلاً متن آزادند؛ جمع‌آوری و تأیید فنی در Codex انجام می‌شود. نمره کیفی و نمودار زنده در پنل پیاده نشده‌اند. این مرزها برای جلوگیری از اشتباه گرفتن دفتر کار با سیستم انتشار خودکار مستند شده‌اند.
