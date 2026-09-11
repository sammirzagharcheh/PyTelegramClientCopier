# Applying taste-skill to Telegram Client Copier

Project-specific decisions. This file is ours; everything under `skills/` is a
verbatim upstream copy and must never be edited. When upstream changes, update
`skills/` wholesale and revisit this file (see `UPSTREAM.md`).

## Design read

Following `skills/taste-skill/SKILL.md` section 0.B:

> Reading this as: a preserve-mode redesign of an internal operations dashboard
> for Telegram channel copying, for technical operators who live in it daily,
> with a restrained Linear-style language, leaning toward Tailwind v4 CSS-first
> semantic tokens and CSS-only motion.

## Dials

`skills/taste-skill/SKILL.md` section 1, tuned by section 1.A and section 7.

| Dial | Value | Reason |
|---|---|---|
| `DESIGN_VARIANCE` | 3 | Section 1.A puts accessibility-critical and trust-first work at 3-4. Operators scan the same tables every day, so predictable structure beats asymmetry. |
| `MOTION_INTENSITY` | 3 | Section 5 says that if you cannot ship real motion in scope, drop the dial to 3 and ship clean and static rather than half-built. At 3 the allowance is hover and active states only, which is what a dashboard should have. It also means no animation library dependency. |
| `VISUAL_DENSITY` | 7 | Section 7 describes 4-7 as standard app spacing and 8-10 as cockpit density. This app is closer to cockpit than to marketing, so 7, and section 7 additionally mandates monospace numerals at this density. |

## Scope limit, stated honestly

Section 13 of `skills/taste-skill/SKILL.md` puts dashboards, dense product UI,
admin panels, and data tables **out of scope** for the skill, and instructs the
agent to say so explicitly rather than apply landing-page rules anyway. This
application is entirely dashboards, admin panels, and data tables.

So the following parts of the skill are **not** applied here, by the skill's own
instruction:

- Hero composition rules (sections 4.7, 4.9): there is no hero anywhere.
- Marketing image strategy (section 4.8): no Picsum placeholders, no stock
  photography, no ambient background imagery. Decorative imagery in a control
  panel is noise, and every pixel here is operational.
- Eyebrow, marquee, bento, logo-wall, testimonial, and zigzag rules
  (sections 4.3, 4.10, 9.F): none of those patterns exist in this app.
- The section 2.A design-system swap: replacing Tailwind with Carbon or Fluent
  would be a rewrite of 77 files for no user-visible gain.

What **is** applied, because it is stack-independent and holds for any UI:

- Section 4.2 colour calibration and the colour consistency lock.
- Section 4.4 shape consistency lock and shadow restraint.
- Section 4.5 full interactive state cycles, plus the mandatory button and form
  contrast checks.
- Section 4.6 form patterns (label above input, error below, never
  placeholder-as-label).
- Section 6.B reduced motion, 6.C dark mode, 6.F z-index restraint.
- Section 8 dark mode protocol, including the no-pure-black and no-pure-white
  rule.
- Section 9 AI tells, including the section 9.G em-dash ban.
- Section 11 redesign protocol in preserve mode: audit first, keep the
  information architecture, keep the brand accent, do not regress accessibility.
- All of `skills/redesign-skill/SKILL.md`, which is written for exactly this
  situation and is where most of the concrete fixes came from.

## Where upstream conflicts with this project, and who wins

The brief's precedence order is accessibility, functionality, maintainability,
and established project standards, ahead of the skill.

| Upstream rule | Decision | Reason |
|---|---|---|
| `skills/taste-skill/SKILL.md` 3.C and `skills/minimalist-skill/SKILL.md` 2 discourage `lucide-react` | Keep Lucide | Section 3.C's own override allows it when the project already depends on it. It does, in 40-plus files. Swapping icon libraries is churn with no user benefit. Section 3.C's actionable part, one family and a standardised `strokeWidth`, is applied. |
| Section 3.A mandates Motion (`motion/react`) for animation | No animation library | At `MOTION_INTENSITY: 3` the only motion needed is hover, active, and focus transitions, which CSS does natively. Adding a runtime dependency for that fails the brief's "reuse before adding dependencies" rule. |
| Section 4.1 and `minimalist-skill` 3 push bespoke fonts (Geist, Satoshi, Cabinet Grotesk) | System font stack | Self-hosting a webfont adds build weight and a render-blocking asset to a tool that operators keep open all day, and the app runs on a self-hosted box with no CDN. The typographic substance of the rule, a real weight ramp, tightened display tracking, and tabular numerals for data, is applied without the download. |
| `minimalist-skill` 3 wants an editorial serif for headings | No serif | Directly contradicted by `taste-skill` 4.1 serif discipline, which calls serif-by-default the most-tested AI tell. Sans throughout. |
| `minimalist-skill` 4 specifies a warm monochrome canvas | Cool neutral (zinc) | Section 4.2 requires one grey family, not a specific one. The existing product is cool-grey and blue, and section 11.C says a preserve-mode redesign keeps the existing brand tokens. |
| `minimalist-skill` 5 wants pill-shaped badges but 4-6px buttons | Documented radius rule instead | Section 4.4's shape consistency lock allows a mixed system when the rule is written down and followed. Ours: pills for status badges only, `rounded-md` for controls, `rounded-lg` for surfaces. |
| Section 4.8 image strategy, section 4.7 hero rules | Not applied | Out of scope per section 13, see above. |

## The house rules that came out of this

These are the ones worth knowing before touching `frontend/src`.

1. **Tokens, not literals.** Colour comes from the semantic scale in
   `frontend/src/index.css` (`surface`, `surface-raised`, `surface-sunken`,
   `line`, `ink`, `ink-muted`, `ink-subtle`, `accent`). Do not reach for
   `bg-gray-800` or `text-gray-500` in new code. Tailwind's `emerald`, `amber`,
   and `red` scales stay available, but only for genuine semantic state.
2. **One accent.** Blue, everywhere, for every interactive and active affordance.
   Colour that is not the accent and not a status means something is wrong.
3. **Primitives before markup.** `frontend/src/components/ui/` has `Button`,
   `Modal`, `Field`, `Input`, `Select`, `Textarea`, `Card`, `TableShell`,
   `EmptyState`, `ErrorState`, and the skeletons. Hand-rolling another
   `px-4 py-2 rounded bg-blue-600` button reintroduces the drift this pass
   removed.
4. **Four states per async view.** Loading as a skeleton shaped like the real
   content, empty with a way out, error with a retry, then success. Section 4.5
   treats shipping only the success state as unfinished work.
5. **Zero em-dashes.** Section 9.G, non-negotiable, in UI strings and in code
   comments. Use a hyphen, a comma, or two sentences.
6. **Contrast is checked, not assumed.** Body text at AA against its own
   surface. `text-ink-subtle` is the floor for small text; anything lighter is a
   bug.
7. **Keyboard first.** Every interactive element is a real button or link, has a
   visible `focus-visible` ring, and every overlay traps focus, closes on
   Escape, and returns focus to its trigger.
