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
| GET /api/renders, /api/renders/file | version list / ranged playback |
| GET /api/jobs, /api/job | job list (filter by status) / one job with logs |
| POST /api/jobs | enqueue {kind, payload, idempotency_key?}; unknown kinds rejected |
| POST /api/jobs/decision, /cancel, /retry | approve/reject waiting jobs; cancel; retry failed |

Job kinds: `transcribe_audio`, `edit_detect`, `render_cut` (final kind waits for explicit approval), `publish_dryrun`.

## Data and security boundaries

SQLite (WAL) tables: `content`, `events`, `jobs`, `media`, `transcripts`, `edit_decisions`, `renders`. Raw media lives in `data/media/`, renders in `data/renders/`, dry-run packages in `data/dryrun/` — all inside the gitignored `data/` tree. Originals are never modified or deleted by any pipeline step; deletion has no API. Uploads are token-gated and capped at 20 GB.

Publishing: `publish_dryrun` writes an inspectable JSON package labelled DRY RUN. No public post, OAuth flow or credential exists in this codebase. Analytics ingestion, multi-track media sync and archive moves are not implemented yet.

## Tests

`python -m unittest discover -s tests -v` — 47 tests: storage, install, HTTP gates, media/transcripts, jobs (lifecycle, restart, idempotency, approval gates, honest dependency failures), editing (incl. real-FFmpeg silence fixture), render (cut durations, restore re-render, NVENC, all-cut rejection), triggers, and the critical end-to-end fixture (idea → voice → transcript → decisions → restore → preview → dry-run → FINAL → archive integrity).

`python tests/check_docs.py` — docs links. `node tests/ui-flow.cjs` — real-browser flow: content workflow, media upload, manual transcript version, click-to-seek, manual cut, Persian report, jobs page, restart persistence. Needs an existing Chrome + `PLAYWRIGHT_MODULE`; set `TEHNET_FFMPEG` for the media section.

## حدود نسخه

تبدیل گفتار به متن روی مدل محلی اجرا می‌شود؛ بارگیری اولیه مدل به اینترنت نیاز دارد و کیفیت فارسی به مدل انتخابی وابسته است. تشخیص تکرار/برداشت ناموفق صرفاً «پیشنهاد نیاز به بررسی» است و هرگز خودکار حذف نمی‌کند. همگام‌سازی چند دوربین (Media Sync)، Shorts/Reels، انتشار واقعی، Analytics و آرشیو خودکار هنوز پیاده نشده‌اند و در UI نیز ادعا نمی‌شوند.
