# Third-party provenance / منبع اسکیل‌ها

## OpenCut-AI subtitle export

- Repository: [Ekaanth/OpenCut-AI](https://github.com/Ekaanth/OpenCut-AI)
- Pinned commit: `eb8aef9f971648980673b207fc28eb76955883b3`
- Scope: unchanged `services/ai-backend/app/services/subtitle_service.py`, copied to [opencut_subtitles.py](../outputs/panel/vendor/opencut_subtitles.py)
- License: [MIT, copyright 2025 OpenCut-AI](../outputs/panel/vendor/OpenCut-AI-LICENSE.txt)
- Local wrapper: [captions.py](../outputs/panel/captions.py), handling cut retiming, timestamp quantization and ASS text sanitization. No full application/server was installed.

## Social media skills

- Repository: https://github.com/charlie947/social-media-skills
- Pinned commit: `8cefb5b6d03757885faa6918bd8bfaef202a83db`
- Author/copyright: Charlie Hills, 2026
- License: [MIT](../vendor/social-media-skills/LICENSE)
- Vendored scope: 17 skill directories, including their two bundled reference files; 19 files in total.
- Upstream README: [preserved copy](../vendor/social-media-skills/README.upstream.md).
- Checksums: [manifest](../outputs/installation-manifest.json).

The upstream skill files are unchanged. The installer verifies the manifest before copying and preserves existing destinations. Local Persian rules are supplied through AGENTS.md, brand profiles and generated prompts.

نسخه اصلی اسکیل‌ها دست‌نخورده است. فارسی‌سازی و تصمیم‌های کاربر در سیاست پروژه اعمال می‌شوند. فایل‌های مخزن منبع دستور کار Agent هستند؛ به معنی انتقال حساب‌ها، مدل‌ها یا سرویس خصوصی نویسنده نیستند.

The manifest records successful historical installation on the original workstation. Its paths were normalized to repository-relative vendored paths for public documentation. Runtime installation status must be checked on each machine.
