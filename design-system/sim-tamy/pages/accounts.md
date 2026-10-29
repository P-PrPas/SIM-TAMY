# Account and dashboard screens — 2026-10-29

Uses `../MASTER.md` without changing the brand. Ivory canvas `#fcfaf6`, white surfaces, dark brown
`#30261b`, gold `#efbd51`, and self-hosted Noto Sans Thai. Reuse control/card/panel radii and existing
buttons, cards, async states and source-backed progress data. No chart or authentication dependency.

- Login: one primary submit action; a separate panel offers a native disclosure and grouped account
  dropdown that fills the form without signing in. Use visible labels, password-manager autocomplete,
  a password visibility control, inline errors, and a clearly labeled demonstration boundary.
- Navigation: the account control lives at the top right and opens profile/logout actions. Learner
  navigation excludes the former Passport item; institution navigation exposes only the workspace.
  Institutional tools use one sidebar; on phones it becomes an inline navigation block.
- Learner profile: identity first, three measured activity counts, then four native progress bars for
  the curated lesson/simulation pairs. Repeated attempts never fill unrelated stages. Keep all finished
  attempts and completed lessons below, with Critical Safety shown independently per attempt.
- Institution: organization totals and recent classes, with separate routes for cohorts, assignments,
  analytics and existing staff settings. Destructive actions require inline confirmation and preserve
  learning evidence; no controls for editing accounts or institution metadata in this scope.
- Mobile: compact metric cards, 44px targets, no clipped names or horizontal overflow, and no duplicate
  primary action in the login header. Honor reduced motion and keyboard/Escape behavior.

References rechecked: [Navbar Gallery](https://www.navbar.gallery/) for dropdown/sidebar structure,
[CTA Gallery](https://www.cta.gallery/) for form/action hierarchy,
[HeroInspo](https://heroinspo.com/) for the split composition, and
[Skooldio](https://www.skooldio.com/) for a distinct login entry beside learning navigation.
These inform layout only; no assets, claims, metrics or clinical copy were copied.

The initial design-system search returned a children's claymorphism direction, which does not fit
this audience. The narrower data-dashboard result informed grouping and density only. Radar-chart
guidance was unsuitable for completion tracking; native progress bars keep the recorded numerator
and denominator explicit without suggesting competence or averaging safety.
