# SIM-TAMY design system

Scope: T-050–T-056, FR-CASE-02, FR-I18N-01, PRD §5.2. The implementation source for tokens is `apps/web/app/globals.css`.

## Direction

Warm editorial education: calm, credible, and welcoming. Use the supplied logo unchanged, with gold, ivory, and dark brown. Avoid clinical marketing claims, invented statistics, testimonials, ornamental animation, and generic technology gradients.

Inspiration reviewed:

- [Skooldio](https://www.skooldio.com/): learning-oriented information hierarchy and clear entry points.
- [HeroInspo](https://heroinspo.com/#galleri): a spacious split hero with a distinct brand composition.
- [Navbar Gallery](https://www.navbar.gallery/): concise navigation with one subordinate instructor entry.
- [CTA Gallery](https://www.cta.gallery/): clear action labels and a focused enrollment panel.

The ui-ux-pro-max education/editorial search matched Minimalism & Swiss Style. Its spacing and hierarchy guidance fit this product; the generic pink palette and Latin font pairing did not. The implementation instead uses the supplied gold logo and a Thai font. No reference components or assets were copied.

## Tokens

| Role | Token | Value |
| --- | --- | --- |
| Canvas | `canvas` | `#fcfaf6` |
| Surface | `surface` | `#ffffff` |
| Body | `ink` | `#302b25` |
| Secondary text | `muted` | `#6c6458` |
| Border | `line` | `#e6dfd4` |
| Primary action | `brand-950` | `#30261b` |
| Gold action | `gold` | `#efbd51` |
| Gold text and focus | `brand-700` | `#7c5314` |
| Soft brand surface | `brand-100` | `#f8edcf` |

Gold buttons use dark text. Success, warning, and error retain their semantic colors with written labels; never infer safety from a color or total score. The `stone-*` scale contains warm neutral values shared by the existing application components.

## Typography and layout

- Self-hosted variable Noto Sans Thai, with its SIL Open Font License in `apps/web/app/fonts/OFL.txt`. No external runtime font requests.
- Base 16px, body line height 1.75, reading copy 16–18px; compact navigation, badges, and supporting labels may be smaller.
- Thai headings wrap naturally with progressive `text-wrap: balance`; no forced nonbreaking spaces.
- Desktop content maximum 1248px including gutters. Gutters 20px on phones, 32px on desktop. Shared spacing follows the existing 4/8px scale.
- Split hero, three learning benefits, and a single enrollment form. At small widths, stack these in reading order.
- Controls at least 44px in the shared navigation, with 48px form fields. Existing workflow buttons retain generous padding and visible focus states.
- Restrained 180ms color/elevation feedback. Honor reduced motion; avoid entrance effects that delay interaction.
- Shared header/footer and five noninteractive progress steps keep orientation consistent across learning screens. Progress steps describe position rather than permit skipping required decisions.

## Motion

- The hero copy and brand artwork enter in two stages (640ms, 100ms offset) with the shared arrival easing. The artwork settles in place; there is no continuous floating or parallax.
- Next.js `template.tsx` replays a short 280ms entrance when changing learning pages. The home hero uses its own entrance instead of stacking both effects.
- The current progress marker settles into place once. Fine-pointer hover gives feature cards a slight lift; main CTA buttons have press feedback and a single gold sweep on hover or keyboard focus.
- Typing dots pulse only while a chat request is in flight. Message content itself remains still, and the existing readable live status remains available to assistive technology.
- Reduced motion disables animations and transitions, cancels hover movement, and preserves the final readable state immediately. Print output also disables motion. No animation completion event controls application behavior, and no animation library was added.

## Copy and safety

All Thai interface copy stays in `apps/web/lib/i18n/th.json`. Write for learners: explain the action, expected result, and recovery path. Use descriptive scenario names instead of A/C labels. Hide version metadata on the entry and briefing screens; keep report exports intact.

`DEV-001` is excluded from the learner entry and recording gallery. This is presentation filtering, not API access control. Recordings remain explicitly described as examples.

Product-owner update, 2026-10-18: learner screens omit review badges and education disclaimers, including the global banner. Instructor tools and exports retain real case status; drafts are never relabeled as approved. Critical Safety results remain visible. The owner also authorized removing the review suffix from course titles and replacing placeholder personas with course relationships; clinical facts and scoring stay unchanged.

## Verification

Use the repository's Playwright workflow for mobile accessibility and learner journeys. `e2e/brand.spec.ts` adds desktop, landscape, reduced-motion, enlarged-text, asset-loading, navigation, and overflow checks, and captures entry/briefing screenshots for visual inspection. Unit coverage protects engineering-fixture filtering and descriptive variant labels.

Validated locally on 2026-10-18:

- `npm.cmd run typecheck`, `npm.cmd run build`: passed.
- `npm.cmd run lint`: no errors; one existing unused-variable warning in `tests/api-client.test.ts`.
- `npm.cmd test`: 80 tests passed.
- `npm.cmd run test:e2e`: 19 tests passed against Prism / mocked session responses, including the existing serious/critical axe gates. Entry and briefing screenshots inspected at 360px, landscape 844px, and desktop 1440px.
- Backend pytest: 502 passed, 172 skipped because PostgreSQL was unavailable. Engine coverage gate passed at 99%. Windows' default temporary-directory permissions required an explicit workspace-local `--basetemp` with its parent directory created first.
- Content validator: all seven cases passed.
- `git diff --check`: passed.

Motion follow-up: typecheck, lint, 80 unit tests, content validation, and backend pytest (502 passed / 172 database-dependent skips) were rerun. The browser suite passed its existing 19 checks; the additional motion check initially exposed an overly literal test assertion (`none` versus an equivalent identity transform matrix). It now checks the matrix's actual identity and passed on a focused rerun, including live reduced-motion changes and CTA interaction. No application animation behavior was changed to satisfy that assertion.

GNU make was unavailable, so the commands defined by `make test` and `make validate-content` were executed directly with the repository virtual environment and npm scripts. Docker startup, live database journeys, and real-LLM runs were not verified. No backend, clinical content, scoring, schema, or dependency changes were made.
