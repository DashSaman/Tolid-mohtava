# Tehran Network & MyTel Content Room

[فارسی](README.md) · [Technical reference](docs/TECHNICAL.md) · [Work log](docs/CHANGELOG.md)

A local **Persian, right-to-left** content workspace for ideas, scripts, recording transcripts, sources, and version-specific human approvals. Includes 17 pinned Codex content skills and separate **Tehran Network / tehnet.ir** and **MyTel / mytel.one** profiles.

**Actual capability:** content editing, SQLite persistence, revision history, explicit brand sharing, script/publication approval records, JSON export, and personalized skill prompts work. Local automation also works end to end on this machine: immutable media upload, local speech-to-text (faster-whisper, GPU when CUDA libs are present), conservative non-destructive edit decisions with real restore, preview/final rendering (FFmpeg, NVENC when available), a persistent job queue with live progress, and a labelled DRY-RUN publication package. Nothing is ever published to the internet; real publishing adapters, notifications, and live analytics remain **not connected** and are not claimed anywhere.

![Persian dashboard](docs/images/dashboard.png)

## Quick start

Requires **Python 3.10+**. The panel uses only the standard library: no pip dependencies, Docker, Node, or API key. Git is needed only to clone. Running the content skills requires Codex and the tools needed by the selected skill route.

```bash
git clone https://github.com/DashSaman/Tolid-mohtava.git
cd Tolid-mohtava
python scripts/install_skills.py
python scripts/start_panel.py
```

On Windows, use `py -3` instead of `python` if needed, or double-click **Open-Panel.cmd** after installing Python. Default URL: **http://127.0.0.1:8766**. The launcher only starts this panel; it does not start/reconfigure GrowthOS, WSL, or Docker.

For environments that block automatic browser opening: `python scripts/start_panel.py --no-browser`, then open the URL yourself. For foreground diagnostics: `python outputs/panel/server.py`.

The offline installer checks the vendored checksums and copies the 17 skills into project-local `.agents/skills`. It **preserves every existing skill directory**. Optional global installation: `python scripts/install_skills.py --global`; choose one discovery route rather than installing conflicting copies. All 17 were already installed globally on the original workstation. Start a fresh Codex turn in this repository so it can load the skills and project instructions.

## Daily workflow

1. Select Tehran Network or MyTel in the sidebar.
2. Click “محتوای جدید” (New content), enter your idea/script, and save.
3. Open “۱۷ اسکیل” (17 skills), choose a skill and source content, and enter this task's request.
4. Generate and copy the Persian instruction package; run it in a fresh Codex turn in this project.
5. Paste the generated result back into the content record. After recording, keep the actual transcript as the source of truth.
6. Review the exact revision and target brands in the approval center; approve the script and publication separately.

The Codex round trip is currently manual. No button pretends to run an AI provider or publish externally.

## Every panel section

| Persian label | Purpose |
|---|---|
| داشبورد | Content count, pending/approved publication records, installed skill count, recent records, production flow |
| فضای کاری | Brand selector; filters records to the selected brand |
| محتوا | All content, title search, details, and brand-specific history export |
| سناریوها | Records in script, recording, editing, or repurposing stages |
| تقویم کار | Proposed work dates; not an automated publishing scheduler |
| مرکز تأیید | Records with either approval gate not yet approved |
| ۱۷ اسکیل | Real skill purpose, dependencies, project adaptation, installation status, and prompt builder |
| تحلیل عملکرد | Separate YouTube, Instagram, Telegram, Facebook, LinkedIn, and Website tabs; missing data is unavailable |
| SEO | Prepublication checklist and the recorded DispatchSEO address; no automated crawler |
| منابع | Sources saved in the selected brand's records |
| اعلان‌ها | Local review requests only; no Telegram/email delivery |
| هویت و تنظیمات | Read-only brand identity, voice, visual profile, policy; edit canonical project files through Codex |
| Agentها و سرویس‌ها | Historical discovery evidence and existing service links; not live health monitoring |

## Every button and field

| Control | Behavior |
|---|---|
| + محتوای جدید / + ثبت ایده | Open a new content form |
| همه محتواها / انتخاب اسکیل | Navigate to all content or skills |
| جست‌وجوی عنوان | Filter titles within the current brand/view |
| بررسی / پرونده محتوا | Show exact text, revision, brands, transcript, sources, notes, and event history |
| ویرایش محتوا | Edit the selected record, creating a new revision on save |
| Title | Required; maximum 200 characters |
| Platform | Proposed target; does not connect an account |
| Stage | Idea, research, technical verification, script, recording, editing, repurposing, SEO, or ready for review |
| Brand checkboxes | Select one brand or explicitly share one record across both brands |
| Main text | Idea/script/output that will be versioned and approved |
| Actual transcript | Recording transcript; preferred source for subsequent content work |
| Transcript file input | Import TXT/MD up to 500 KB; does not transcribe audio |
| Sources / technical verification | Plain-text source URL, software version, review date, and result |
| Notes | Missing facts, questions, and content flags |
| Proposed date | Internal work date only; no scheduler or external reminder |
| ذخیره محتوا | Persist to SQLite, append a history snapshot, reset both approvals to pending |
| × | Close dialog; unsaved changes are not preserved |
| تأیید همین نسخه — script gate | Record approval of this exact script revision for recording |
| تأیید همین نسخه — publication gate | Record approval of this exact publication revision; no external API call |
| رد | Record rejection for that revision and gate |
| نیاز به بررسی | Mark that gate as requiring further review |
| تاریخچه | Expand timestamps, event types, and revisions; full old snapshots remain in JSON export |
| خروجی و تاریخچه این برند / دریافت خروجی برند و تاریخچه | Download this brand's records and full history as JSON; UI import is not implemented |
| باز کردن میز اسکیل / بسته دستور تحلیل | Open the selected skill's inputs and prompt builder |
| Source content selector | Attach only the selected record from the current brand |
| This task's request | Tell Codex what you want it to do |
| آماده‌سازی دستور فارسی | Compose skill instructions, policy, profile, and source content; no model invocation |
| کپی دستور | Copy to clipboard; select text for Ctrl+C if browser permissions block copying |
| Analytics platform tabs | Switch platform context without fabricating metrics or connecting an account |
| Service links | Open the recorded address; never start/restart a service |
| Full audit / guide links | Open local text documentation |
| Open-Panel.cmd | Start this repository's loopback panel with installed Python |
| Backup-Panel.cmd | Create a consistent SQLite backup under outputs/backups |

![17-skill workspace](docs/images/skills.png)

## The 17 skills

Pinned upstream: [charlie947/social-media-skills](https://github.com/charlie947/social-media-skills), commit `8cefb5b6d03757885faa6918bd8bfaef202a83db`. Original files are preserved under `vendor` with Charlie Hills' MIT license. Project adaptations live in the policy/profiles, not in modified upstream skill files.

| Skill | Actual purpose and dependencies | Project adaptation |
|---|---|---|
| [`voice-builder`](vendor/social-media-skills/skills/voice-builder/SKILL.md) | Voice profile from interview and 3–5 writing samples | Reuse prior answers; requested Persian voice is configured, sample-derived personal voice is unverified |
| [`newsletter-voice`](vendor/social-media-skills/skills/newsletter-voice/SKILL.md) | Newsletter style from existing profiles plus samples or an archetype | Optional; do not invent samples or sign-offs |
| [`profile-optimizer`](vendor/social-media-skills/skills/profile-optimizer/SKILL.md) | LinkedIn profile copy and four visual prompts; real profile, evidence, and headshot | Verified biography only; draft without changing the account |
| [`post-writer`](vendor/social-media-skills/skills/post-writer/SKILL.md) | LinkedIn post drafting from topic, about-me.md, and voice.md | Persian copy, technical sources, real CTA, platform-specific versions |
| [`graphic-designer`](vendor/social-media-skills/skills/graphic-designer/SKILL.md) | Editable HTML graphic or image prompt; renderer/generator for actual assets | RTL, mobile legibility, distinguish prompts from inspected images |
| [`post-formatter`](vendor/social-media-skills/skills/post-formatter/SKILL.md) | PAS/AIDA/BAB/STAR/SLAY post formatting | Do not impose LinkedIn length constraints on long video scripts |
| [`reels-scripting`](vendor/social-media-skills/skills/reels-scripting/SKILL.md) | Reference-based short scripts; transcript route or optional Apify/Gemini/Node video route | Actual recording transcript is authoritative; production markers and technical review |
| [`youtube-thumbnail`](vendor/social-media-skills/skills/youtube-thumbnail/SKILL.md) | YouTube thumbnail brief/Gemini prompt; real content, reference photo, branding | Title, thumbnail and hook share an honest promise |
| [`post-scorer`](vendor/social-media-skills/skills/post-scorer/SKILL.md) | Editorial review or comparison against supplied/authorized LinkedIn history | Explain scores; include technical/SEO/brand fit; score is not publication permission |
| [`analytics-dashboard`](vendor/social-media-skills/skills/analytics-dashboard/SKILL.md) | LinkedIn XLSX analysis; React/Recharts for its interactive dashboard route | Separate brands/platforms; weekly analysis target; never treat absent metrics as zero |
| [`pinned-comment`](vendor/social-media-skills/skills/pinned-comment/SKILL.md) | Upstream: four-line deadpan comment and image prompt | Useful conversation plus a soft next step; image-dependent comedy is not mandatory |
| [`hook-generator`](vendor/social-media-skills/skills/hook-generator/SKILL.md) | Six concise hook angles using supplied facts | Best agent recommendation plus three selectable packages; no misleading clickbait |
| [`content-matrix`](vendor/social-media-skills/skills/content-matrix/SKILL.md) | 3–5 content pillars × eight formats | Separate brand matrices; prioritize demand, audience questions, and business relevance |
| [`niche-research`](vendor/social-media-skills/skills/niche-research/SKILL.md) | Dated niche stories from the past seven days; live web or supplied sources | Technical preproduction research can need more than news; official sources first |
| [`gemini-carousel`](vendor/social-media-skills/skills/gemini-carousel/SKILL.md) | Slide briefs and Gemini prompts after approval | Persian slides; inspect every generated slide |
| [`gemini-infographic`](vendor/social-media-skills/skills/gemini-infographic/SKILL.md) | Whiteboard infographic brief and Gemini prompt | Preserve technical coverage, Persian readability, relevant CTA |
| [`quote-post`](vendor/social-media-skills/skills/quote-post/SKILL.md) | Nine short quote options and a reference-style image prompt | Relevant professional content, no fabricated attribution or performance promises |

Installation badges check the actual project-local/global SKILL.md hash. A clone is not an installation. Full 19-file integrity is checked by the installer/tests and recorded in the manifest. Customized installations are preserved and not falsely marked as the pinned version.

## Agents, existing services, and installation scope

| Component | Actual state |
|---|---|
| Codex | Runs skills in chat; not an API backend connected to the panel |
| 17 skills | Newly installed on the original workstation; 19 exact upstream files |
| Python/SQLite panel | Newly authored application; reused existing Python and standard library |
| OpenHands | Referenced in existing GrowthOS files; recorded URL localhost:8000/canvas/; live connection unverified |
| DispatchSEO | Referenced at localhost:4005; no new installation |
| Activepieces | Referenced at localhost:8080; workflows unchanged |
| Uptime Kuma | Referenced at localhost:3001; not live-monitored here |
| Ollama | Referenced in the existing launcher; endpoint unavailable from the audit environment |
| LM Studio | Existing folders/models found: DeepSeek-R1-0528-Qwen3-8B-GGUF and Meta-Llama-3-8B-Instruct-GGUF; no model downloaded |
| DashSaman/-SEO | Existing local evidence-led documentation discovered for reuse |
| Gemini / Apify | Optional skill-route dependencies; no new account/SDK/key or paid run configured |
| Chrome / Playwright | Existing browser/testing tools reused; no new browser installed |
| WSL / Docker | WSL inspection denied; full container inventory and update requirements remain unknown |

File evidence is not proof of a running service. The [audit](outputs/audit.fa.md) records overlaps, gaps, all requested service names, and eventual credentials without secrets.

## Brand and approval rules

The [policy](outputs/content-policy.fa.md) implements the [supplied requirements](outputs/master-prompt.fa.md). Brand profiles are under [Tehran Network](outputs/brands/tehran-network/about-me.md) and [MyTel](outputs/brands/mytel/about-me.md). Persian conversational tone is requested, not falsely claimed to be learned from writing samples. Shared videos open with Tehran Network and use contextual MyTel sponsorship without a permanent sponsor logo. Technical claims require evidence; thumbnail/title/hook share one promise.

Script and publication gates are independent. Editing resets both approvals. Stale approvals/edits are rejected. Repeating the same approval is idempotent. Shared records require explicit selection of both brands.

![Approval screen with educational test data](docs/images/approval-demo.png)

This screenshot comes from an isolated test database, not real or published content.

## Architecture and data

```text
Persian browser → loopback HTTP → Python standard library → local SQLite
        ↓
Skill + brand profile + policy prompt → copy to Codex → save returned output
```

`outputs/panel/data/content.sqlite`, backups and runtime content are ignored by Git. JSON exports contain full history but cannot currently be imported through the UI. Use `Backup-Panel.cmd` or `python outputs/panel/backup.py` for consistent SQLite backups. To restore, stop only this panel, preserve the previous DB, then copy a backup to the DB path.

Optional environment variables: `TEHNET_PANEL_PORT` (default 8766), `TEHNET_PANEL_DB` (alternate DB path), `CODEX_HOME` (global skill discovery). The backup helper targets the default DB; use SQLite's backup API for a custom DB path.

This is a single-user, local-only application. It has no internet-facing/multi-user authentication. Mutations require a local session token and allowed Host/Origin; user text is escaped; DB/source files are not HTTP-served; there is no publication endpoint. Product UI is Persian; developer CLI output may be English.

## Repository map

```text
README.md / README.en.md    Persian and English manuals
AGENTS.md                  Project agent contract
Open-Panel.cmd             Windows launcher
Backup-Panel.cmd           Windows backup entry point
scripts/                   Portable installer and launcher
outputs/panel/             Server, store, registry, HTML/CSS/JS
outputs/brands/            Independent brand profiles
outputs/*.md               Requirements, policy, audit, verification
outputs/installation-manifest.json  Pinned source and checksums
vendor/social-media-skills/ Original skill files and license
docs/images/               UI screenshots and labelled test example
docs/                      Technical reference and work log
tests/                     Storage, installation, HTTP and browser tests
```

## Verification

```bash
python -m unittest discover -s tests -v
python tests/check_docs.py
node --check outputs/panel/app.js
```

Optional real-browser workflow: `node tests/ui-flow.cjs` with existing Node, Playwright, and Chrome. Set `PLAYWRIGHT_MODULE` to an existing package path and `PYTHON` to the Python executable when needed. No automatic dependency installation. Test data is isolated under ignored `work/`.

[Technical/API reference](docs/TECHNICAL.md) · [Work log](docs/CHANGELOG.md) · [Original test evidence](outputs/verification.fa.md)

## Mobile

<img src="docs/images/mobile.png" alt="Persian panel at mobile width" width="320">

## Not implemented yet

Complete WSL/account audit; secure model/transcription adapters; automated editing/repurposing; publication adapters with idempotency; email/Telegram notification delivery; live analytics ingestion and evidence-based scheduling. These are gaps, not installed or connected capabilities.

## Attribution and licensing

Third-party skills: Charlie Hills, [MIT](vendor/social-media-skills/LICENSE); see [provenance](docs/THIRD_PARTY.md). No separate open-source license has yet been declared for the custom panel. The upstream skill license does not license the entire project.
