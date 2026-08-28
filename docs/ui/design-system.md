# Kora Design System

Kora's UI is a dark, data-dense, "glowing terminal" aesthetic: near-black panels with a single accent blue, monospace labels in wide letter-spacing, soft glow shadows on interactive/positive elements, and geometric (non-figurative) glyphs in place of an icon library. It originated as a Claude-Design visual export and has since been implemented directly against the real app — every screen in `frontend/src/components/kora/screens/` is built from the primitives documented here, wired to real backend data (never sample data).

Source of truth for the values below:
- `frontend/tailwind.config.tokens.js` — colors, fonts, letter-spacing, shadows, gradients
- `frontend/src/components/kora/primitives.tsx` — the primitive components
- `frontend/tailwind.config.ts` — how the tokens are merged into the Tailwind theme (see the comment there about the `accent` color merge with shadcn's pre-existing `accent`)

## Principles

- **Dark by default, one accent color.** The whole app runs on a near-black ink background with a single blue accent (`accent.DEFAULT`, `#4D8DFF`) used consistently for focus, primary actions, and "in-progress/positive" signal — never introduce a second brand color.
- **Monospace for structure, sans for prose.** Section labels, field labels, badges, and kickers are set in JetBrains Mono with wide tracking; headings and body copy are set in Geist. This is what gives the UI its "instrument panel" feel — don't set body prose in mono, and don't set labels in sans.
- **Geometric glyphs, not an icon library.** There is no `lucide-react`/icon-font usage in the Kora screens themselves (it remains a dependency for not-yet-migrated shadcn scaffolding only). Status and decoration are built from plain divs/borders (see `EmptyState`'s placeholder square) rather than pulled-in icon glyphs.
- **Glow means "alive."** `shadow-glow-*` is reserved for the active/selected/positive state of an element (a focused tab, a filled progress bar, a success toast) — it is a signal, not decoration, so don't apply it to static content.
- **Build primitives, don't one-off Tailwind.** Every screen should compose the primitives in `primitives.tsx`. If a new pattern is needed twice, add a primitive rather than duplicating a class string.

## Color tokens

Defined in `frontend/tailwind.config.tokens.js`, used via Tailwind classes like `bg-ink-950`, `text-fg-dim`, `border-accent/30`.

| Group | Tokens | Use |
|---|---|---|
| `ink` | `950` (app background), `900` (sidebar top), `850` (popovers/chat/modals), `800` (chat bottom gradient) | Surface backgrounds, darkest to less-dark |
| `accent` | `DEFAULT #4D8DFF`, `bright`, `soft`, `pale`, `ghost`, `deep`, `ink` (text-on-filled-accent) | The one brand color — buttons, focus rings, active tab underline, links |
| `fg` | `DEFAULT` → `secondary` → `tertiary` → `quiet` → `muted` → `dim` → `faint` → `ghost` → `disabled` | Text, ordered brightest to dimmest — pick the dimmest tone that's still legible for the content's importance |
| `danger` | `DEFAULT`, `soft`, `pale`, `wash`, `ink` | Errors, high-severity findings, destructive actions |
| `warn` | `DEFAULT`, `soft`, `pale`, `wash` | Medium-severity findings, "flagged" states |
| `good` | `DEFAULT`, `pale`, `wash` | Success states, positive metrics, completed status |

## Typography

```js
fontFamily: {
  sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
  mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
}
letterSpacing: {
  label: '0.14em',   // mono section labels (SectionLabel, FieldLabel)
  kicker: '0.16em',  // breadcrumb/eyebrow text (Kicker)
  badge: '0.08em',   // badge/button text
  tight: '-0.9px',   // large page headings
}
```

Page headings use `font-sans` at 32px with `tracking-tight`; every label-style element (`SectionLabel`, `FieldLabel`, `Kicker`, badges) uses `font-mono` in uppercase with the corresponding tracking value above.

## Shadows & gradients

`boxShadow` tokens (`glow-accent`, `glow-accent-lg`, `glow-danger`, `glow-warn`, `glow-good`, `panel-pop`, `modal`, `chat`) and `backgroundImage` tokens (`panel-sheen`, `hero-accent`, `hero-warn`, `accent-btn`, `accent-rail`, `sidebar`) are all defined in `tailwind.config.tokens.js`. Use the named token (`shadow-glow-accent`, `bg-panel-sheen`) rather than hand-rolling an equivalent box-shadow/gradient, so a future palette tweak only requires editing the token file.

## Primitives (`src/components/kora/primitives.tsx`)

All primitives are plain, unstyled-prop React components — they take `children`/data props, not style overrides, so visual consistency is enforced by construction.

**Surfaces**
- `Panel` — the base card/container (rounded, hairline border, near-transparent white fill). Almost everything sits inside one.
- `PanelHeader` — a panel's title row with an optional `aside` (e.g. an action button) on the right.

**Type**
- `PageHeading` — `kicker` + large `title` + optional `blurb` + optional `action` (top of every screen).
- `Kicker`, `SectionLabel`, `FieldLabel` — mono, wide-tracking labels at decreasing size (breadcrumb-style → section header → form field label).

**Badges & chips**
- `Badge` — pill badge, `tone: 'neutral' | 'accent' | 'danger' | 'warn' | 'good'`.
- `SeverityBadge` — maps a `Severity` (`high`/`medium`/`low`) to the matching `Badge` tone automatically.
- `SourceBadge` — labels a finding's provenance (`document-stated` / `kora-inferred` / `deterministic`).
- `StatusBadge` — maps a free-text status string to a tone (`completed` → accent, `failed` → danger, else neutral).
- `Chip` — softer, non-pill tag for lists of values (`tone: 'neutral' | 'danger' | 'good'`).
- `GapChip`, `GapRow` — dashed-border "missing data" markers, used by coverage/missing-information UI.

**Buttons**
- `PrimaryButton` — filled accent-gradient button with glow, for the one primary action on a screen. Takes `type: 'button' | 'submit'` (defaults to `'button'`) — pass `type="submit"` when it drives a form so Enter-to-submit works.
- `GhostButton` — outlined button, `tone: 'accent' | 'neutral' | 'danger'`, for secondary actions.

**Data display**
- `Meter` — thin animated progress bar, `tone: 'accent' | 'warn' | 'good' | 'danger'`, optional `markerAt` for a threshold tick.
- `StatCard` — the dashboard/summary KPI card (label, large value, optional badge, tone-colored top rule).
- `MetricCell` — a labeled value in a data table/grid, with an optional `flagged` badge.
- `FactField` / `FactChips` — labeled field + chip-list rendering for extracted document facts.

**Findings**
- `FindingCard` — the validation-finding card (colored left rail + frame by severity, `SeverityBadge` + `SourceBadge`, title, optional `metricRef`, detail text). Has a `compact` variant for denser lists.

**Misc**
- `EmptyState` — dashed-border placeholder for empty lists/screens, with optional `action`.
- `Tabs<T>` — underlined tab bar (`size: 'sm' | 'md'`), generic over the tab id type so callers get type-safe `active`/`onSelect`.
- `Toast` — success toast shell (the app's actual toasts run through `sonner`, themed via `toastOptions.classNames` in `app/providers.tsx` to match this look, rather than rendering this component directly).
- `LoadPulse` — a top-of-panel gradient pulse for loading state.

## Motion

Small CSS-animation utility classes are used sparingly and consistently: `kora-rise` (fade/rise-in for page headings and cards on mount), `kora-grow-x` (progress bar fill animation, used by `Meter`), `kora-slide-in` (toast entrance), `kora-pulse` (loading pulse, used by `LoadPulse`). Reuse these class names rather than introducing new keyframe animations for the same purpose.

## Working with the design system

- Prefer composing existing primitives over new Tailwind class strings; if you need a new visual pattern, add it to `primitives.tsx` so every screen can reuse it.
- Keep new colors, shadows, and gradients as named tokens in `tailwind.config.tokens.js` rather than inline arbitrary values (`bg-[#4D8DFF]`), so the palette stays centrally editable.
- Screens (`src/components/kora/screens/*`) should stay presentational — they receive already-fetched data and callbacks as props from the page component in `app/(protected)/*`, which owns the React Query hooks. This keeps the design-system layer free of data-fetching concerns.
