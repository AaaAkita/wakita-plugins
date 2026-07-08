---
name: avoid-assumption-loops
description: Prevent spiraling trial-and-error by verifying assumptions before iterating, especially when tuning visual/layout parameters.
metadata:
  type: feedback
---

**Rule:** Before making iterative adjustments to spacing, sizing, colors, or any visual/layout parameter, first verify that the mechanism actually works and that my change is observable.

**Why:** In a layout-breathing task, I assumed `px-6`, `px-8`, etc. utility classes existed because they look like Tailwind, but this project uses a hand-written utility set without those classes. I iterated on padding values for multiple turns, showed screenshots, and argued about spacing while the computed `padding-left/right` was `0px` the entire time. This wasted the user's time and patience.

**How to apply:**
- When a CSS/HTML class change does not produce the expected visual effect, stop and inspect the computed style via browser dev tools, preview_eval, or equivalent — do not guess a new value.
- Before relying on any utility class (especially `px-*`, `py-*`, `mx-*`, `gap-*`), grep the stylesheet to confirm it is defined.
- After any visual tweak, validate with a measurement or computed-style check, not just a screenshot impression.
- If the same adjustment fails twice, stop iterating and diagnose the mechanism (missing class, specificity conflict, cached file, wrong selector) before trying a third value.
