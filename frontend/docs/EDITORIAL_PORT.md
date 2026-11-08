# Editorial baseline port — local integration notes

## Source and branch boundaries

This frontend presentation branch starts from published `main` at `0e92899ce54f85440fe920ca457dfd91f747e1aa`.

- Shared technical foundation: `feat/fe/editorial-baseline`.
- Requested feature pattern: `feat/<number>-<feature>-fe` for frontend and `feat/<number>-<feature>-be` for backend.
- Login Admin frontend belongs to `feat/1-login-admin-fe`, branching from the tested local foundation commit. Its backend counterpart is planned, not implemented or represented by an empty placeholder branch.
- Features 6 and 7 must later have separate FE/BE branches. The pre-existing combined local React checkpoint is preserved; this port does not republish it or claim that its backend integration is complete.

The team's root README currently describes feature PRs to `main`; the requested `fe`/`be` integration flow still needs team agreement and synchronization. At discovery, both integration branches were five commits behind the source main. Do not push this branch, make a PR against a stale destination, or change shared refs automatically. No push, PR, merge or backend permission is implied by the local foundation commit.

## What changed

The selected Prototype 2 paper/ink palette, exact self-hosted Inter Tight/Archivo fonts, hero composition, visual assets, manifesto and contextual imagery are ported to React. The existing API-backed summary and Recharts trend component remain in use. `src/api.ts`, its endpoints, and backend source/database files are unchanged. Prototype fixture values are not imported into the application.

Presentation-bound fixes were reproduced before repair:
- A one-point sparkline no longer yields NaN coordinates; missing history is explicit rather than a fabricated zero series.
- API observation dates are labelled Observasi, not official publication release dates.
- Missing sources are not labelled official; an empty response has an explicit state.
- The API card adapter accepts backend string identifiers without casting them into the static chart-tab enum.
- Dead detail navigation is explicitly unavailable until the separate feature-6 frontend integration. Login Admin is likewise not implemented on this foundation branch.

Existing illustrative insight copy is clearly labelled as unverified design-reference narrative, not live API/AI analysis. The existing chart's aggregation/average logic is inherited from the team implementation, not a newly verified backend formula. A frontend build is not evidence that economic formulas, source provenance or provider data are correct.

## Reproduce checks

From `frontend/`:

- `npm ci --ignore-scripts --no-audit --no-fund` installs the committed lockfile locally without lifecycle scripts. This install mode was exercised successfully for this port; dependencies and lockfile were not upgraded.
- `npm test` runs the new targeted React server-render regression tests using installed Vite and Node's test runner.
- `npm run build` runs the actual TypeScript/Vite build.
- `npm run lint` runs the repository's Oxlint command. Record existing warnings separately from exit status; do not silently suppress them.
- `npm run test:browser` starts its own temporary frontend server and disposable Chrome profile. `CHROME_BIN` can select an already installed Chrome. This suite intercepts the known local API request paths with explicitly synthetic DTOs; it does not start Django, call ingestion/provider endpoints or prove live-data integration.

Browser output defaults to ignored `frontend/.artifacts/browser/`. `DEKSI_BROWSER_ARTIFACTS` selects another output directory; `HERMES_TEST_SCRATCH` selects the permitted scratch directory for disposable profiles. Tests close only their own browser/server. The normal dev preview can be started with the existing `npm run dev` command.

The browser suite checks actual chart geometry before captures, correct trend endpoint selection, explicit empty/error states, no horizontal overflow at tested widths, source-dialog Escape/return focus and reduced motion. Human review of the integrated React appearance remains separate. These are targeted port checks, not the whole product's BDD, backend, provider, accessibility or performance certification.

## Assets and publication gate

`src/assets/editorial/credits.json` records the original photo sources, artists, licenses and crop/monochrome/feathering changes. Source and license links are accessible through the frontend disclosure. Per-photo CC BY/CC BY-SA obligations remain applicable; do not apply one blanket license to every asset. OFL texts for the two fonts are included beside their WOFF2 files.

The user-selected public hero is preserved byte-for-byte from the approved local baseline. Its original is low resolution and its publication rights remain unconfirmed. It is included only in the authorized local recovery commit; resolve rights or obtain approval for a cleared replacement before public publication. Do not silently replace the chosen visual or claim that interpolation recovered native detail.

Standalone prototypes, original photo downloads, ZIPs, local evidence/plans, node_modules, dist, credentials and runtime databases are not part of the staged source allowlist.
