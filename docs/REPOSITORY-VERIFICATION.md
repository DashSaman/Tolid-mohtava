# Repository verification / تأیید نسخه مخزن

Date: 2026-09-26. These checks apply to the packaged repository, not to external providers.

| Check | Result | Evidence |
|---|---|---|
| Standard-library test suite | PASS | 9 tests: storage, stale writes/approvals, independent gates, explicit brand sharing, installer preservation, vendor checksums, HTTP boundaries |
| Browser user journey | PASS | Existing Chrome + Playwright: create, save, brand isolation, HTML escaping, approve both gates, edit/invalidate, search, JSON export with four history snapshots, server restart/persistence |
| JavaScript syntax | PASS | node --check outputs/panel/app.js |
| Documentation and images | PASS | 74 maintained relative links; dashboard, mobile, skills and labelled approval screenshots exist |
| Original installation provenance | PASS | 17 skills, 19 unchanged upstream files; pinned commit and SHA-256 manifest |
| Workstation path removal | PASS | No original user's home path in tracked project source/docs; runtime discovery derives local paths |
| Sensitive runtime data exclusion | PASS | No SQLite DB, backups, .env, log, credential or test runtime data included in repository payload |
| Provider/social integrations | NOT VERIFIED | No provider execution, upload, publication or live analytics tested |

Screenshot caveat: dashboard/mobile show the original empty workstation panel. Skills and approval examples were captured from the packaged app. The approval example uses clearly labelled synthetic content in an isolated database. No private production content appears in these images.

The local panel running on the original device remains unchanged by the repository packaging. The repository version adds portable startup/install helpers and checks actual skill installation status per machine.
