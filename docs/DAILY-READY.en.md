# Daily release guide — 13 October 2026

Launch `Start-Tolid-Docker.cmd`, then open http://127.0.0.1:18767 using the existing panel credentials. This machine runs the linked `tolid-docker` checkout on `ready/2026-10-13`. Earlier reports and screenshots describe historical releases.

Media and renders use D:\Tolid-Mohtava. Live SQLite stays in the Docker named volume; do not open it directly from Windows. `Backup-Tolid-Docker.cmd` creates an integrity-checked snapshot and SHA256 under D:\Tolid-Mohtava\backups. Original C: copies were retained. The optional archive mount requires My Passport to be connected.

Choose a brand, create a project, upload source speech/video, transcribe, generate and review content, inspect proposed silence/text cuts, render previews/finals/shorts, then approve the specific revision. RAW is preserved. Review AI factual claims against actual sources. Ollama qwen3.5:4b supplies local text tasks. In Settings, benchmarking uses an uploaded short Persian voice file and its correct reference text; small/medium are compared. large-v3 requires a separate model download.

A ready YouTube channel is not an API connection. `Connect-YouTube.cmd` records the Google OAuth Web client locally. Enable YouTube Data API v3 and authorize redirect http://127.0.0.1:18767/oauth/callback, then connect and test inside the panel. Uploads use Google's official SDK, are approval-gated and private. Live upload and channel statistics cannot be verified until the owner completes OAuth. Supported statistics are aggregate channel views/subscribers/videos, not detailed retention/watch-time analytics.

WordPress drafts, GSC, GA4 and Gemini require their credentials. Instagram/Facebook/LinkedIn currently provide review packages and manual analytics; OAuth alone does not implement automated publishing/ingestion. No local image-generation model was installed. Full multicamera composition remains outside the single-video workflow; track synchronization stores offsets.

For a merged recording with picture and sound, upload as Screen Recording, open its editing room and choose Analyze and Build Preview. Existing Whisper supplies Persian word timestamps; local Ollama suggests exact duplicate takes and bounded settings-panel zooms. FFmpeg combines conservative silence cuts, audio cleanup and burned-in captions. Commands, numbers, negation, different steps, instructional waits and sampled silent screen activity are protected; new automatic cuts share a 20% source budget. Uncertain or invalid regions produce no zoom.

Review the preview, transcript and cuts. Restore inappropriate cuts or uncheck zooms, then build a fresh preview without repeating AI analysis. Download SRT/VTT. Request the final and approve that specific plan in the approval center. Changes to transcript/cuts invalidate the snapshot; rendering locks manual mutations and validates again before registering output. Optional Shorts use the edited final timeline and preserve the whole tutorial frame over a blurred background. Up to two are produced when suitable transcript cues exist. Caption accuracy depends on source speech and the chosen model; manually entered text lacks precise word timing. Nothing is published by this workflow.

Existing FFmpeg, faster-whisper, cached models and Ollama were reused. [Auto-Editor](https://github.com/WyattBlue/auto-editor) overlaps with existing silence removal, so no duplicate stack was installed. Only the pinned MIT subtitle serializers from [OpenCut-AI](https://github.com/Ekaanth/OpenCut-AI) were reused; local wrappers remap times and neutralize ASS commands. The full application was not installed. See [provenance](THIRD_PARTY.md). Sixteen pre-existing missing-media records and historical job failures were preserved.


## Docker storage relocation on this installation

With owner approval, the Docker Desktop disk now resides under D:\DockerDesktopData\disk. The former C: disk directory redirects through an NTFS junction. Source/destination SHA256 matched before restart, and the original disk remains under D:\DockerDesktopData\rollback-20261013. All previously running containers were restarted. Do not modify either directory while Docker runs.

Existing panel credentials are in Documents\Tolid-Mohtava-Admin-Credentials.txt under the same Windows account; the password was preserved.
