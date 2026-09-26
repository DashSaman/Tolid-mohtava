# Tehran Network / MyTel workspace contract

Read `outputs/content-policy.fa.md` and `outputs/master-prompt.fa.md` before content work. Reuse prior answers. Read the selected brand's `about-me.md`, `voice.md`, and `brand-kit.md` under `outputs/brands/`. Valid brand IDs: `tehran-network`, `mytel`.

User decisions override conflicting skill defaults: Persian/RTL, independent brands, transcript as source of truth, factual verification, contextual sponsorship, and per-version human approval. Never invent biography, samples, metrics, source checks, credentials, provider activity or publication success.

The 17 unmodified upstream skills live under `vendor/social-media-skills/skills`. Install with `python scripts/install_skills.py` into `.agents/skills`; preserve existing installations. A clone alone does not install or activate a skill. Read the actual loaded SKILL.md and referenced files. Audit/adaptation mapping: `outputs/panel/skills.json`.

Do not alter GrowthOS, WSL, Docker, existing services, external accounts or production websites as part of local panel work. Public publishing and external messages require the user's explicit authorization. Local approval records never automatically publish.

Never commit local databases, backups, .env, API keys, tokens or runtime content. Keep runtime state in ignored directories. Source and static project documentation are tracked; real content is not. Third-party skills retain their MIT license.

Run `python -m unittest discover -s tests -v`, `python tests/check_docs.py`, and the HTTP/browser tests when changing relevant behavior. Update bilingual docs and capability status honestly. UI is Persian; English documentation must explain the same features and limitations.
