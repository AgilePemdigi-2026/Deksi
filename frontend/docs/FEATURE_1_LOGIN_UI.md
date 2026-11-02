# Feature 1 — Login Admin frontend

## Branch and dependency
- Branch: `feat/1-login-admin-fe`.
- Depends on local shared foundation commit `505e97116f132c8630ec08d07525b8aec9e00536` (`feat/fe/editorial-baseline`), originally based on main `0e92899ce54f85440fe920ca457dfd91f747e1aa`.
- This feature is a frontend-only React port of the approved editorial login prototype. It is not a backend implementation or a remote PR.
- Future backend work belongs on `feat/1-login-admin-be` when separately authorized; no empty backend branch was created.

## Behavior and boundaries
- `/` remains the public API-backed dashboard without an account gate.
- `/admin/login` renders the React login UI, also accepting a trailing slash. The public footer links to it; the login header/footer return to `/`.
- Mounting the login page does not mount dashboard API hooks.
- Identifier and password are required. Identifier whitespace is checked; password content is not trimmed and no backend password policy is invented.
- The password visibility toggle preserves typed input and exposes its state accessibly.
- Errors focus the relevant field. Keyboard navigation, native recovery disclosure and native source dialog are implemented; Escape returns focus to the dialog trigger.
- Successful local validation explicitly says authentication is not connected and no session has been created. No authentication request, credential log, application storage write, registration or real password reset is implemented. Do not use real credentials on this prototype.
- Backend authentication, CSRF/session design, Admin authorization and production routing are separate work. This route is on the frontend origin and does not modify Django's own Admin routes.

## Visual/media provenance
- Approved monochrome paper palette, typography, photo composition and desktop hierarchy retained. Narrow viewports are the same responsive website, not another application.
- `src/assets/editorial/login-economic.webp` is byte-identical to the approved 1920 × 2560 Pexels collage, SHA-256 `54d0c30b26a5347750f518d369ec4bf8c17df93c7a9310d59dcaa79a7265bf87`.
- `src/assets/editorial/login-media.json` retains original source URLs/dimensions and source-verification limitations. No unverified photographer name is promoted to a verified credit. The image is illustration, not economic evidence or endorsement.
- Page styles are scoped under `.login-page`. Existing `src/api.ts`, lockfile, backend and protected feature 6/7 checkpoint were not changed.

## Executed checks
- `npm test`: 12 Node/Vite-SSR tests passed, including 7 inherited foundation cases and 5 login/navigation/validation cases.
- `npm run build`: TypeScript and production Vite build passed. Existing large-chunk warning remains; no limit was raised or suppressed.
- `npm run lint`: zero errors; the three existing warnings in EconomicSummary, API and TrendChart remain. No new warning was introduced by the login code.
- `npm run test:browser:login`: 6 grouped Chrome browser scenarios passed. Synthetic input only. Checks include zero credential requests/storage, focus/errors, show/hide, source/recovery controls, both navigation directions and reduced-motion behavior.
- `node tests/browser.test.mjs`: 5 dashboard browser-regression groups passed on this feature worktree with explicitly synthetic API responses, including chart selection and empty/error states. These are not live economic data or Django integration checks.
- Desktop 1440px and responsive 390/760/1024px captures were inspected; no horizontal overflow was measured. Native-browser test profiles/servers are disposed by the harness.
- `npm run test:browser` runs both browser scripts. The two scripts were executed separately above to retain distinct evidence and avoid redundant reruns.

## Review and remaining gates
- The user reviewed and accepted the current integrated React dashboard and Login UI in this session, acknowledging that unavailable API data can leave charts without values. This visual approval is not backend acceptance or full accessibility certification.
- Authentication/backend/database integration and live-source economic accuracy are unverified.
- This feature is saved as a separate local checkpoint on its feature branch under the user's explicit commit approval. No push or PR is authorized by that checkpoint; consult Git history for the exact commit.
- Before any publication, resolve public-dashboard hero rights, agree the team PR base (`main` versus synchronized `fe`/`be`), and obtain the applicable commit/push/PR authorization. No shared ref was updated.
