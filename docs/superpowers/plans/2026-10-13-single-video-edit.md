# Single-video educational editing implementation plan

> Execution: implement directly in the existing `ready/2026-10-13` worktree; the owner approved the complete design and execution in this conversation.

**Goal:** A merged audio/video recording produces a reviewable local preview, then an explicitly approved final and optional Shorts.

**Architecture:** Reuse FFmpeg, faster-whisper and the configured local Ollama model. Store immutable review plans in existing SQLite; compare source checksum, transcript revision, cuts, options and zooms before registering a render. Reuse only OpenCut-AI's MIT subtitle serializers.

**Constraints:** Persian/RTL; RAW immutable; commands, numbers, negation, instructional waits and silent screen activity preserved; no new paid API/model; no external publishing; existing services unchanged.

**Review focus:** fractional frame timing after many cuts; both duplicate takes removed by overlapping cuts; changed commands/negation; stale approvals during rendering; subtitles and Shorts using the edited timeline.

## Tasks and verification

- [x] `video_edit.py`, `visual_edit.py`: validate local AI suggestions against source evidence; reject unsafe repeat/region suggestions. Test waits, screen activity, IPs, commands, cycles and retained references.
- [x] `captions.py`, `transcribe.py`, `vendor/`: preserve word timestamps; remap SRT/VTT/ASS through retained intervals; neutralize ASS overrides. Test fractional timestamp carry and removed words.
- [x] `video_render.py`: compose cuts, bounded zooms, audio cleanup and subtitles; allocate frames by cumulative output time. Test real FFmpeg, many fractional cuts, unchanged source and rejected render cleanup.
- [x] `auto_video.py`, `server.py`: persist plans, preview first, final approval gate, stale checks before registration, optional Shorts from final timeline; protect manual mutations during rendering.
- [x] `app.js`: single-video controls, zoom deselection, fresh preview, subtitle downloads and approval preview link; choose actual video instead of idea audio.
- [x] Verify full unittest suite, documentation, JS syntax, real local model/transcription/preview/final/Shorts and browser controls; deploy only the content panel after backup and zero active jobs. Results: [verification](../../SINGLE-VIDEO-VERIFICATION.md).
- [x] Update bilingual current-status docs with verified results and account requirements. Commit/push and the existing draft PR are the final handoff step.
