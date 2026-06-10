---
name: radar
description: Adds high-value tests, fixes flaky tests, and improves coverage with minimal and reliable changes. Use when tests are missing, unstable, or insufficient.
---

## Overview
This skill improves test reliability and coverage without changing product behavior.

It focuses on adding the smallest useful tests, fixing instability, and increasing confidence in the system.

---

## 1. Choose the Right Target First

Before writing tests:

- Identify high-risk areas (edge cases, errors, async logic).
- Prioritize uncovered or weakly tested behavior.
- If unclear, ask what should be protected.
- Avoid testing low-impact or trivial code first.

**Do not write tests without a clear purpose.**

---

## 2. Test Behavior, Not Implementation

Write tests that validate what the system does, not how it is built.

Avoid:

- Testing private/internal functions directly
- Over-mocking internals
- Asserting implementation details

Prefer:

- Inputs → outputs
- Public interfaces
- Observable side effects

---

## 3. Keep Tests Simple and Isolated

Each test must:

- Have its own setup and cleanup
- Not depend on execution order
- Avoid shared mutable state

Guidelines:

- Use clear structure (Arrange → Act → Assert)
- Keep tests small (< 50 lines if possible)
- Use deterministic data (no randomness, no real time)

---

## 4. Fix Flaky Tests Properly

When tests fail intermittently:

- Find the root cause before fixing
- Common causes:
  - async timing issues
  - shared state
  - order dependency

Avoid:

- Adding arbitrary delays
- Blind retries

Prefer:

- Proper async handling (`waitFor`, retries with context)
- Isolation of state
- Deterministic timing (mocks, fake timers)

---

## 5. Add High-Value Coverage

Focus on:

- Edge cases (null, empty, limits)
- Error paths
- Branch conditions (true/false cases)

Do not:

- Chase coverage numbers blindly
- Add redundant tests

Ask:

*"Does this test catch a real possible failure?"*

---

## 6. Regression Safety First

When fixing bugs:

1. Write a test that fails (reproduces the bug)
2. Apply the fix
3. Ensure the test passes

**Never fix bugs without locking them with a test.**

---

## Expected Behavior

This skill is working correctly if:

- Tests are stable (no flaky failures)
- Coverage improves in meaningful areas
- Tests remain simple and readable
- Bugs are protected with regression tests
- No unnecessary or redundant tests are added

---

## Example Usage

**User request:** "Add tests for this function"

**With this skill:**

1. Identify missing edge cases
2. Add minimal high-value tests
3. Ensure isolation and determinism
4. Avoid over-testing internals

---

**User request:** "Tests are failing randomly"

**With this skill:**

1. Identify flaky root cause
2. Remove nondeterminism
3. Stabilize async behavior
4. Verify consistent results
