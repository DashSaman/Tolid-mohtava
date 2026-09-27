# Technical reference / راهنمای فنی

## Runtime

Python 3.10+, standard library only for the panel itself. Optional local engines are detected at runtime and never downloaded by the panel: faster-whisper (speech-to-text, GPU via CUDA wheels when present) and FFmpeg/FFprobe (silence scan, rendering; located via PATH, `TEHNET_FFMPEG`, or the winget package dir). NVENC is used for final renders only when `ffmpeg -encoders` actually lists `h264_nvenc`. Missing engines produce honest `BLOCKED_BY_DEPENDENCY` job failures, never fake output.

| Variable | Default | Meaning |
|---|---|---|
| TEHNET_PANEL_PORT | 8766 | Loopback HTTP port |
| TEHNET_PANEL_DB | outputs/panel/data/content.sqlite | SQLite database location |
| TEHNET_FFMPEG | auto-detect | Explicit ffmpeg binary path |
| CODEX_HOME | ~/.codex | Global skill discovery root |
| PLAYWRIGHT_MODULE | playwright | Optional browser-test package path |
| PYTHON | python | Python executable for browser tests |

## Modules

| File | Responsibility |
|---|---|
| store.py | Content transactions, validation, version conflicts, independent approvals, history and export |
| jobs.py | Persistent job queue: queued/running/waiting_approval/completed/failed/cancelled, progress, logs, retry, cancel, approval gates, idempotency keys; restart marks interrupted runs failed and re-dispatches queued ones |
| media.py | Immutable media ingest (voice/screen/face/external_audio/broll): streamed upload, sha256, content linkage, verify() |
| transcribe.py | faster-whisper adapter (auto GPU→CPU fallback, CUDA-DLL discovery), versioned transcripts per media, timed-text parser for manual entry |
| editing.py | Conservative non-destructive edit decisions: FFmpeg silencedetect + filler/repeat heuristics; auto-activate only clear defects, borderline cases proposed; restore/dismiss survive re-analysis; Persian report |
| render.py | trim/concat filter from merged active cuts; preview (720p) and final (1080p, NVENC when present, faststart); renders table with EDIT V1..N / FINAL Vn labels |
| triggers.py | publish approval → exactly one dry-run package per content+revision; double-approve safe; no external calls |
| shorts.py | Short/Reel candidate heuristic from real transcripts + 9:16 render (blurred background composite, no blind crop) |
| publishing.py | WordPress REST draft adapter for tehnet.ir / mytel.one (both verified WordPress on 2026-09-27); runs only after explicit job approval AND environment credentials (WP_<SITE>_USER / WP_<SITE>_APP_PASSWORD); otherwise honest BLOCKED_BY_CREDENTIAL |
| system.py | /api/health real component statuses + bounded GPU probe; /api/storage drive enumeration (ctypes) incl. My Passport label detection |
| avtools.py | ffmpeg/ffprobe/NVENC detection |
| server.py | HTTP allowlist, JSON endpoints, Host/Origin/token checks, CSP, ranged file streaming |
| registry.py | Read-only detection of project-local or global skill files |
| index.html / app.js / style.css | Persian RTL UI incl. media editing room and live jobs page |
| backup.py | SQLite backup API for the default database |

## HTTP API

All URLs are local. No permissive CORS. Every request requires the correct Host. Mutations require `Content-Type: application/json` (raw binary only for `/api/media`), an allowed Origin when present, and `X-Panel-Token` from `/api/session`.

| Method / route | Purpose |
|---|---|
| GET /api/session | App marker + per-process mutation token |
| GET /api/skills | 17 definitions + real install status |
| GET/POST /api/items | Content list / create-update |
| POST /api/decide | gate script/publish × pending/approved/rejected/review; publish approval auto-enqueues its dry-run job |
| GET /api/history, /api/export, /api/profile, /api/policy | unchanged ledger surfaces |
| POST /api/media | raw media upload (X-Media-Kind/Name/Mime/Content-Id, ≤20 GB) |
| GET /api/media, /api/media/file | media list / ranged streaming of the immutable original |
| POST /api/transcripts | manual transcript entry (lines like `1:23 متن` become segments); new revision per save |
| GET /api/transcripts | latest or all (`&all=1`) versions for a media |
| GET /api/decisions, /api/editreport | decision list / Persian report lines |
| POST /api/decisions/manual, /api/decisions/state | add manual cut / set decision state (active/restored/dismissed) |
| GET /api/renders, /api/renders/file | version list (all or per media) / ranged playback |
| GET /api/shorts?media_id= | candidate clips derived from that media's transcript |
| GET /api/publishing | per-destination credential status incl. WordPress sites |
| GET /api/storage | real drives, panel data sizes, passport connectivity |
| GET /api/health, POST /api/health/gpu | live component statuses / real CUDA inference probe (cached 10 min) |
| GET /api/assets, POST /api/assets/state | thumbnail assets and approve/reject states |
| GET /api/jobs, /api/job | job list (filter by status) / one job with logs |
| POST /api/jobs | enqueue {kind, payload, idempotency_key?}; unknown kinds rejected |
| POST /api/media accepts kind thumbnail for image assets; media rows carry ffprobe duration when available |
| POST /api/jobs/decision, /cancel, /retry | approve/reject waiting jobs; cancel; retry failed |

Job kinds: `transcribe_audio`, `edit_detect`, `render_cut` (final waits for approval), `render_short`, `publish_dryrun`, `website_publish` (waits for approval; credential-gated).

## Data and security boundaries

SQLite (WAL) tables: `content`, `events`, `jobs`, `media`, `transcripts`, `edit_decisions`, `renders`. Raw media lives in `data/media/`, renders in `data/renders/`, dry-run packages in `data/dryrun/` — all inside the gitignored `data/` tree. Originals are never modified or deleted by any pipeline step; deletion has no API. Uploads are token-gated and capped at 20 GB.

Publishing: `publish_dryrun` writes an inspectable JSON package labelled DRY RUN. No public post, OAuth flow or credential exists in this codebase. Analytics ingestion, multi-track media sync and archive moves are not implemented yet.

## Frontend and CSP

The UI is a no-build vanilla JS app (`index.html`/`app.js`/`style.css` + self-hosted Vazirmatn woff2, OFL). `script-src 'self'` stays strict; `style-src` allows inline styles because layout styles are embedded in generated HTML — XSS remains blocked by output escaping and the strict script policy. Assets use relative paths, so opening index.html via file:// shows a Persian guidance screen instead of a broken page; `Open-Panel.cmd` finds Python (py -3 → python → winget path) and always opens http://127.0.0.1:8766.

## Tests

`python -m unittest discover -s tests -v` — 47 tests: storage, install, HTTP gates, media/transcripts, jobs (lifecycle, restart, idempotency, approval gates, honest dependency failures), editing (incl. real-FFmpeg silence fixture), render (cut durations, restore re-render, NVENC, all-cut rejection), triggers, and the critical end-to-end fixture (idea → voice → transcript → decisions → restore → preview → dry-run → FINAL → archive integrity).

`python tests/check_docs.py` — docs links. `node tests/ui-flow.cjs` — the full user journey in real Chrome: wizard (voice upload → real transcription), timestamped transcript, script save + approval, media upload, manual transcript, edit analysis, cut restore, preview render + 206 ranged playback, approval-gated FINAL render, publish dry-run, jobs/storage/health pages, mobile viewport, zero console errors, screenshots into docs/images. Needs existing Chrome + `PLAYWRIGHT_MODULE`; `TEHNET_FFMPEG` for fixtures; faster-whisper model cached for the transcription step. Deterministic fixtures live in `tests/fixtures/` (SAPI-generated speech, FFmpeg-generated screen clip).

## حدود نسخه

تبدیل گفتار به متن روی مدل محلی اجرا می‌شود؛ بارگیری اولیه مدل به اینترنت نیاز دارد و کیفیت فارسی به مدل انتخابی وابسته است. تشخیص تکرار/برداشت ناموفق صرفاً «پیشنهاد نیاز به بررسی» است و هرگز خودکار حذف نمی‌کند. همگام‌سازی چند دوربین (Media Sync)، Shorts/Reels، انتشار واقعی، Analytics و آرشیو خودکار هنوز پیاده نشده‌اند و در UI نیز ادعا نمی‌شوند.
