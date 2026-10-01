# Implementation Plan — Docker Isolation (2026-10-01)

Branch: `recovery/docker-isolation` (worktree `../tolid-docker`), base `v1.1.0-ui-rc1`.
Per-task files / tests / verification / rollback. TDD where behavior changes; here most tasks are infra — verified by commands.

| # | Task | Files | Verify | Rollback |
|---|---|---|---|---|
| 1 | Worktree+branch | `git worktree add ../tolid-docker -b recovery/docker-isolation v1.1.0-ui-rc1` | `git log -1` | delete worktree |
| 2 | Selective cherry-picks: 989a6d7 (idempotency+refresh), 513346f (ffmpeg stderr root-cause), 9567a2d (shorts clamp), ae3b04e (watchdog), d9756c1+9bfb463+5415347 (UI v4) | history only | unit tests 125/125 | `git reset --hard` |
| 3 | Dockerfile | `docker/Dockerfile` | `docker build` | rm file |
| 4 | Compose | `compose.yaml` | `docker compose config` | rm file |
| 5 | Secrets template+loader | `runtime/secrets/tolid.env.example`, `.gitignore` entry | `docker compose config` shows env_file; grep secrets in git = none | rm |
| 6 | Local boot (DB **copy**) | copy `outputs/panel/data` → `runtime/data-staging` | health on 127.0.0.1:18767 | `docker compose down` |
| 7 | LM Studio connectivity | (none) | in-container curl `host.docker.internal:1234/v1/models` | n/a |
| 8 | Media/Whisper/FFmpeg/Shorts | — | upload+probe+transcribe+render+short via API | n/a |
| 9 | Tailscale sidecar | `docker/tailscale` svc in compose | tailnet IP reachable; login URL flow | remove svc |
| 10 | Migration tooling | `scripts/migrate-to-docker.py` (backup→copy→verify) | integrity+counts equal | delete copy |
| 11 | Host cleanup tooling | `scripts/host-cleanup.py` (firewall rule, proxy, ADMIN_* env) | items absent; panel still up in Docker | re-run old Open-Panel.cmd |
| 12 | Helpers | `Start-/Stop-/Status-Tolid-Docker.cmd` | run them | n/a |
| 13 | Tests | suites vs `127.0.0.1:18767`; docker-specific boot/restart/persist checks | 125/125, e2e, smoke | n/a |
| 14 | Release | tag `v1.2.0-docker-rc1` → merge main | acceptance list | checkout v1.1.0-ui-rc1 |
