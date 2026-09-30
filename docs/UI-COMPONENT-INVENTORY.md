# UI Component Inventory — v4 (2026)

Source of truth: `outputs/panel/style.css` · markup: `outputs/panel/app.js` (+ `index.html` shell).
Rule: reuse these — never duplicate styling for a new page.

| Component | Class(es) | Where rendered | Notes |
|---|---|---|---|
| Button primary | `button.primary` | topbar CTA, hero, approvals | azure gradient, dark text |
| Button default / sm / block / danger / ghost / ok | `button`, `.sm`, `.block`, `.danger`, `.ghost`, `.ok` | everywhere | surf2 base |
| Card | `.card`, `.panel` | all pages | signal top-rule via ::before |
| Card header | `.cardhead > h2` | section titles | waveform strip ::after |
| Status badge | `.badge` + `ok/warn/danger/info/accent/approved/pending/rejected/review` | rows, tables, jobs | right status rule |
| Chip (hero status) | `.chip` + `ok/warn/info/vio` | hero, dashboards | dot + label |
| KPI tile | `.kpis > .kpi` (+`ok/warn/danger`) | dashboard | mono tabular number |
| Stat tile | `.stats > .stat` (+state) | editing/SEO pages | signal corner |
| Pipeline node | `.flow > .fnode` (+`done/active/wait/blocked`) | dashboard | animated conduit when active |
| Legacy pipeline pills | `.pipeline > span` | misc pages | kept for compat |
| List row | `.rows > .rowitem` (`.t`, `.actions`) | projects, approvals, integrations | |
| Table | `.table` | jobs, KB | dense technical |
| Tabs | `.tabs > button.active` | project workspace | pill over bar |
| Stepper | `.stepper > .step` (+`done/now/blocked`) | project header | square dots + dashes |
| Progress | `.progress > .progressfill` | jobs, wizard | azure→teal |
| Skeleton | `.skeleton` | async loads | shimmer |
| Empty state | `.empty`, `.emptystate > .orb` | empty lists / first-run | animated signal orb (emptystate) |
| Dropzone | `.dropzone` | media/thumbnail upload | dashed |
| Decision row | `.decisionrow` + `cut/keep/review` | editing room | left status rule = AI/user state |
| Timechip | `.timechip` | transcript segments | mono LTR, seek |
| Segrow | `.segrow` | transcript list | |
| Asset card | `.assetgrid > .asset` | thumbnails | |
| Toast | `#toasts > .toast` + `ok/err` | global feedback | status rule right |
| Dialog | `dialog`, `.dialog-head`, `.dialog-actions`, `.formgrid`, `.wide` | editor/media/job/confirm/delete | glass |
| Context menu | `details.ctxmenu > .ctxitems > .block` | project rows | glass |
| Login overlay | `.loginwrap > .logincard` | auth mode | glass |
| Wizard steps | `.wizsteps > .w` (+`on/done`) | create flow | |
| Type card | `.typegrid > .typecard` (+`sel`) | wizard brand/type | signal strip when selected |
| Integration card | `.intgrid > .intcard` (+`.intico/.intname/.intpurpose/.intenv`) | settings | truthful states |
| Hero | `.hero`, `.heroline`, `.subline`, `.kicker` | dashboard | command area |
| KV list | `.kv > dt/dd` | job/media details | |
| Banner / note / warnbox | `.banner(.warn)`, `.note`, `.warnbox` | page-level info | |
| Footer | `footer.pagefoot` | shell | |
| File guard | `#fileguard` | file:// open | |
| Grids | `.grid2`, `.grid3`, `.twocol`, `.chiprow`, `.row`, `.spread` | layout utilities | |

Motion/pausing hooks: `body.app-paused`, `@media (prefers-reduced-motion)`.
Recording studio controls (`#rec-start/pause/resume/stop`, `#rec-time`, `#mic-level-bar`, `#mictest-out`) inherit button/progress styling; timer is mono.
