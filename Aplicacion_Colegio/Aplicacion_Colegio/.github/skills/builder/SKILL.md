---
name: builder
description: Builds production-ready, type-safe backend logic, APIs, and data models with strong validation and reliability practices. Use when implementing business logic or integrating external services.
---

## Overview

This skill enforces disciplined, production-quality coding focused on correctness, type safety, and real-world reliability.

It prioritizes:
- Valid domain models
- Safe API integrations
- Minimal but robust implementations

---

## 1. Define Before You Build

Before writing code:

- Define all types, interfaces, and contracts first.
- Identify inputs, outputs, and failure modes.
- Clarify domain complexity (CRUD vs DDD).
- Ask for clarification if requirements are incomplete.
- Highlight tradeoffs (e.g., simplicity vs scalability).

Avoid starting implementation without a clear contract.

---

## 2. Type Safety is Mandatory

All code must be strictly typed.

Rules:

- Never use `any`
- Avoid unsafe type assertions (`as Type`) at boundaries
- Use strict TypeScript configuration
- Validate all external input before usage

Guidelines:

- Types represent business rules, not just structure
- Prefer explicit types over inference when clarity matters

---

## 3. Validate at Boundaries

All external input must be validated.

Use a two-step approach:

1. DTO validation (e.g., Zod `.safeParse()`)
2. Domain validation (inside entities / constructors)

Rules:

- Never trust external data
- Never allow invalid domain objects to exist
- Return structured errors, do not throw uncontrolled exceptions

---

## 4. Keep Domain Always Valid

Domain models must never exist in an invalid state.

- Enforce invariants in constructors or factories
- Reject invalid data immediately
- Avoid partial or “half-built” objects

Ask:
> "Can this object ever exist in a broken state?"

If yes → redesign.

---

## 5. Handle Failures Explicitly

Every boundary must handle errors:

- API calls
- Database access
- External services

Guidelines:

- Categorize errors:
  - 4xx → client issue (no retry)
  - 429 → retry with backoff
  - 5xx → retry with limits
- Limit retries (3–5 max)
- Use idempotency keys for mutations
- Never retry blindly

---

## 6. Write Testable Code

Code must be easy to test:

- Prefer pure functions
- Isolate side effects
- Avoid hidden dependencies

Always prepare:

- Test skeletons
- Edge case scenarios (null, empty, failure)

---

## 7. Keep It Production-Ready, Not Overengineered

Balance quality and simplicity.

Avoid:

- Overusing DDD for simple CRUD
- Premature abstractions
- Complex patterns without need

Ask:
> "Is this complexity justified by the domain?"

---

## 8. Surgical Changes Only

When modifying existing code:

- Change only what is required
- Do not refactor unrelated areas
- Respect existing patterns and structure

You may:
- Remove code only if your change makes it obsolete

---

## 9. API Integration Discipline

When working with external APIs:

- Implement retry logic with limits
- Add circuit breaker behavior when needed
- Handle rate limits properly
- Validate responses before usage

Never assume external systems behave correctly.

---

## Expected Behavior

This skill is working correctly if:

- Code is type-safe and predictable
- Invalid states are impossible
- External failures are handled safely
- Changes are minimal and intentional
- No unnecessary abstractions are introduced

---

## Example Usage

**User request:** "Integrate payment API"

**With this skill:**

1. Define request/response types
2. Validate inputs with schema
3. Implement API call with:
   - retry logic
   - error categorization
4. Ensure idempotency for payments
5. Return safe, structured responses
6. Provide test skeleton

---
