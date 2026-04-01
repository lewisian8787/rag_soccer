# Accessibility Plan

This document tracks accessibility improvements to the Football Form Guide frontend.

## Background

Accessibility (often abbreviated "a11y") is the practice of making web apps usable by people with disabilities — including those who use screen readers, navigate by keyboard only, or have motion sensitivities. The primary standard is WCAG (Web Content Accessibility Guidelines), published by the W3C.

The key principle: if something is communicated visually, there should also be a non-visual way to get the same information.

---

## Pass 1 — Foundations (completed 2026-03-31)

Six changes across three files. No visual changes — all markup only.

---

### 1. Labelled input (`InputBar.tsx`)

**What we changed:** Added a `<label>` element linked to the text input via `htmlFor` / `id`. The label has the Tailwind class `sr-only` ("screen reader only"), which hides it visually but keeps it in the accessibility tree.

**Why it matters:** `placeholder` text is not a label — it disappears when you start typing and many screen readers don't read it at all. A `<label>` is the standard way to give an input a permanent name.

```tsx
<label htmlFor="question-input" className="sr-only">Ask a question</label>
<input id="question-input" ... />
```

---

### 2. Descriptive submit button label (`InputBar.tsx`)

**What we changed:** Added `aria-label="Submit question"` to the submit button.

**Why it matters:** "Kick Off" is fun but ambiguous out of context. `aria-label` overrides the visible text for screen readers, giving a clearer announcement without changing what sighted users see.

```tsx
<button type="submit" aria-label="Submit question" ...>Kick Off</button>
```

---

### 3. Mode toggle group (`App.tsx`)

**What we changed:** Wrapped the Football / FPL buttons in a `<div role="group" aria-label="Mode">`.

**Why it matters:** `role="group"` tells screen readers that these buttons belong together. Without it, a screen reader user hears two disconnected buttons with no sense that they're related choices.

```tsx
<div role="group" aria-label="Mode" ...>
```

---

### 4. `aria-pressed` on mode buttons (`App.tsx`)

**What we changed:** Added `aria-pressed={mode === 'football'}` and `aria-pressed={mode === 'fpl'}` to the respective buttons.

**Why it matters:** The active mode is communicated visually through background colour. `aria-pressed` is the standard way to communicate a toggle button's selected state to a screen reader — it announces "Football, pressed" vs "Football, not pressed".

```tsx
<button aria-pressed={mode === 'football'} ...>Football</button>
<button aria-pressed={mode === 'fpl'} ...>FPL</button>
```

---

### 5. Live region for answers (`AnswerCard.tsx`)

**What we changed:** Added `aria-live="polite"` to the answer container in all three of its states (loading, typing, complete). Also added `role="alert"` to the error state.

**Why it matters:** When content appears dynamically (without a page reload), screen readers won't notice it unless you explicitly mark the region as "live". `aria-live="polite"` means: "when this area updates, read it aloud at the next natural pause." `role="alert"` is for errors and reads immediately.

```tsx
<div aria-live="polite" ...>   // answer / loading states
<div role="alert" ...>         // error state
```

---

### 6. Reduced motion for animations (`AnswerCard.tsx`)

**What we changed:** Replaced `animate-bounce` with `motion-safe:animate-bounce` on the bouncing football emoji. Added `aria-hidden="true"` to the decorative emoji spans.

**Why it matters:** Some users (those with vestibular disorders, epilepsy, or motion sensitivity) enable "Reduce Motion" in their OS settings. Tailwind's `motion-safe:` prefix automatically disables the animation when that preference is set — no JavaScript needed. `aria-hidden` prevents the emoji from being announced as content by screen readers.

```tsx
<span aria-hidden="true" className="motion-safe:animate-bounce ...">⚽</span>
```

---

## Known remaining gaps (future passes)

| Issue | Impact | Effort |
|---|---|---|
| History sidebar items have no accessible name beyond query text | Low | Low |
| Confidence dot in sidebar is colour-only | Medium | Low |
| No keyboard trap prevention when sidebar is open on mobile | Medium | Medium |
| Focus is not moved to answer after submission | Medium | Medium |
| No skip-to-main-content link | Low | Low |
