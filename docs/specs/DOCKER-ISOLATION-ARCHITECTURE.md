# Tolid-Mohtava — Docker Isolation Architecture Spec (2026-10-01)

Target: run the whole product in Docker Compose; eliminate ALL host-native Tolid remote-access footprint. Rollback point: `v1.1.0-ui-rc1`.

## 1. Services
- **tolid-web** — the existing stdlib panel (`outputs/panel/server.py`) + in-process job workers (current queue is thread-based inside the server process; a separate worker service is NOT required — `tolid-worker` omitted).
- **tolid-tailscale** — dedicated remote-access sidecar (official `tailscale/tailscale` image).
No other services (no invented microservices).

## 2. Networks
- `tolid_internal` (bridge, internal). Sidecar joins the same network. NO `network_mode: host`, no privileged, no docker.sock, no broad host mounts.

## 3. Ports
- Container app port: native `8766` inside the container (safe there; host 8766 conflict is irrelevant).
- Host publish: **`127.0.0.1:18767` ONLY** (loopback binding in compose). Never 8766 (AutoClaw), never 0.0.0.0. Fallback choice if occupied: 18768.
- Sidecar: no host port publish at all (tailnet handles reachability).

## 4. Volumes / persistence
- `tolid-data` bind mount → `./outputs/panel/data` (DB, media, renders — stays on host disk; no giant copies into named volumes).
- `tolid-ts-state` named volume → `/var/lib/tailscale` (sidecar identity; never reuse host Windows Tailscale state).

## 5. Database
- SQLite WAL at `outputs/panel/data/content.sqlite` via bind mount. Migration path: verified backup → **copy** → Docker runs against copy → integrity + counts verified → only then switch to the real file. `PRAGMA integrity_check` before/after.

## 6. Media/RAW
- Host bind mount `./outputs/panel/data` (read-write for web). No deletion ever; no baking into image.

## 7. Secrets
- `runtime/secrets/tolid.env` (gitignored) — contains ONLY `ADMIN_USER` + `ADMIN_PASSWORD_HASH` (hashed form; no plaintext). Loaded via compose `env_file`. No secrets in image/compose/Git/logs. No Windows Registry dependency.

## 8. LM Studio
- Stays on host (127.0.0.1:1234). Container reaches it via `http://host.docker.internal:1234/v1` (Docker Desktop host-gateway). Verified by a real API call from inside the container. LM Studio binding untouched.

## 9. GPU
- Prefer WSL2 GPU passthrough if `docker info` exposes NVIDIA runtime; otherwise **CPU_FALLBACK** (whisper CPU works). No host driver changes.

## 10. FFmpeg
- Installed inside the image (pinned `johnvansickle` static build or apt ffmpeg). Verify `ffmpeg -version` in-container.

## 11. Whisper
- `faster-whisper==1.2.1` pinned in image (+ CPU wheels). Models cached in a `tolid-hf-cache` volume to avoid re-downloads.

## 12. Authentication
- Existing `ADMIN_USER`/`ADMIN_PASSWORD_HASH` env mechanism, sourced from `runtime/secrets/tolid.env`. Auth stays REQUIRED (sessions 12h, rate-limited). Local loopback access also authenticated (consistent + safe).

## 13. Tailscale sidecar
- Official image, `TS_STATE_DIR=/var/lib/tailscale`, own auth (one-time login URL printed by `docker logs tolid-tailscale`). TUN-mode (cap NET_ADMIN + /dev/net/tun) so the tailnet can reach container ports privately; `socat` forwards sidecar:8766 → `tolid-web:8766` over Docker DNS. HTTPS `serve` only if tailnet certs become available; otherwise plain HTTP inside the encrypted WireGuard tunnel — documented, tailnet-only. **Funnel never.** No Windows firewall rule needed (no host port involved).

## 14. Local access
- `http://127.0.0.1:18767` from the host browser only.

## 15. Remote access
- Tailnet devices → sidecar's tailscale IP:8766 → socat → tolid-web:8766 (Docker DNS) — ADMIN-authenticated. Host proxies/firewall rules NOT in the path.

## 16. Backup/restore
- Existing `setup/Backup-TolidMohtava.ps1` still valid (bind-mounted data dir stays on host). Restore = stop stack, restore folder, start.

## 17. Rollback
- `git checkout v1.1.0-ui-rc1`, `docker compose down`, run `Open-Panel.cmd` (legacy native path). Data untouched (same files).

## 18. Host cleanup (after Docker PASS only)
- Remove Tolid firewall rule `Tolid-Mohtava-Tailnet-Only`; stop/remove `scripts/tailscale_proxy.py` process + Open-Panel-Remote dependency; delete Tolid ADMIN_* user env/registry values. Keep: Windows Tailscale app, global firewall, AutoClaw, unrelated env.

## 19. Migration procedure
spec → plan → worktree(branch recovery/docker-isolation @ v1.1.0-ui-rc1) → selective cherry-picks (idempotency 989a6d7, shorts fixes 513346f+9567a2d, UI v4 d9756c1+5415347+9bfb463 if clean) → Dockerfile/compose → local boot on DB COPY → regression → sidecar → real-DB switch → host cleanup → helpers → tests → release v1.2.0-docker-rc1.

## 20. Acceptance criteria
As per mission list: local PASS via `Start-Tolid-Docker.cmd`, host bind 127.0.0.1 only, dedicated port (not 8766), remote = docker sidecar (no host proxy / no firewall rule / no registry auth), AutoClaw + other services UNCHANGED, DB/RAW/projects INTACT, LM Studio/Whisper/FFmpeg/Shorts/AUTH PASS, Funnel disabled, public exposure NONE.
