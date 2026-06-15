---
name: flow
description: Implement UI animations (hover, transitions, loading, gestures) with performance and accessibility in mind.
---

## Purpose
Add meaningful motion that improves feedback and usability.

---

## When to Use

- Hover / press / click effects
- Loading states (spinners, skeletons)
- Modal or page transitions
- Gesture interactions (drag, swipe)

---

## Core Rules

- Prefer CSS (transform, opacity)
- Avoid layout-changing properties (width, height, top, left)
- Keep animations fast (150–300ms)
- Use motion only for feedback, not decoration

---

## Performance

- Target 60fps
- Use GPU-friendly properties only
- Avoid too many simultaneous animations
- Limit `will-change` usage

---

## Accessibility

- Respect `prefers-reduced-motion`
  - Reduce or remove animations
- Never block user interaction with animation

---

## Workflow

1. Identify interaction (hover, click, transition)
2. Choose:
   - duration (150–300ms)
   - easing (ease-out preferred)
3. Apply animation (CSS or minimal JS)
4. Add reduced-motion fallback

---

## Output Format

- Code snippet (CSS / JS / framework)
- Short explanation
- Reduced-motion behavior

---

## Behavior

Good:
- Smooth, simple, fast animations
- Improves UX feedback

Bad:
- Overly complex motion
- Animations that hurt performance
