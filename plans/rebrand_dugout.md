# Plan: Rebrand to The Dugout (Green Theme)

## Context

The app is currently named "Football Form Guide" with an amber accent colour and a generic dark
zinc background. The rebrand renames it to "The Dugout", introduces a green brand colour (emerald),
and adds a subtle football pitch line overlay to the background to give the UI a football-native feel.

---

## Scope

### 1. Page background — pitch overlay
- Replace the plain `bg-zinc-950` page background with a dark green base (`#0a1a0e`)
- Layer a faint football pitch SVG (centre circle, halfway line, penalty areas, 6-yard boxes)
  over the full viewport at ~6% opacity
- Implemented via a `.pitch-bg` CSS class in `index.css` referencing `/pitch-lines.svg`

### 2. Amber → emerald (brand colour swap)
Only interactive/brand elements change. Semantic confidence colours (amber = medium confidence)
are intentionally left untouched.

| File | Change |
|---|---|
| `App.tsx` | Football mode button: `bg-amber-500` → `bg-emerald-500`; stats chip dot + legend dot: `bg-amber-500` → `bg-emerald-500` |
| `InputBar.tsx` | Input focus border: `focus:border-amber-500` → `focus:border-emerald-500`; submit button: `bg-amber-500 hover:bg-amber-400` → `bg-emerald-500 hover:bg-emerald-400` |

### 3. Header — name + logo
- `h1` text: "Football Form Guide" → "The Dugout"
- Replace ⚽ emoji `<span>` with `<img src="/logos/dugout-green.png" …>`
- Logo: 40×40px, `object-contain`

### 4. Page title
- `index.html` `<title>`: "frontend" → "The Dugout"

---

## Files changed

- `frontend/public/pitch-lines.svg` — new file
- `frontend/index.html`
- `frontend/src/index.css`
- `frontend/src/App.tsx`
- `frontend/src/components/InputBar.tsx`

## Files unchanged

- `AnswerCard.tsx` — no brand amber; emerald already used for high-confidence badge
- `HistorySidebar.tsx` — no brand amber; amber used only for medium-confidence semantic dot
- `StandingsTable.tsx` — no amber at all

---

## Out of scope

- FPL mode button stays purple (separate product identity)
- Confidence badge colours (high/medium/low) are semantic — unchanged
- Copy / tagline changes — not requested
- Logo variants (red, blue, purple) — available in `/public/logos/` for future use
