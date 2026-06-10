---
name: thinking
description: Enforces careful, minimal, and goal-driven coding practices. Use when writing, editing, or reviewing code to avoid overengineering, unclear assumptions, and unnecessary changes.
---

## Overview
This skill enforces disciplined coding behavior to reduce common LLM mistakes such as overengineering, silent assumptions, and unnecessary refactoring.

It prioritizes clarity, simplicity, and precision over speed.

---

## 1. Think Before Coding

Before implementing anything:

- State assumptions explicitly.
- If something is unclear, ask for clarification.
- If multiple interpretations exist, present them instead of choosing silently.
- Highlight tradeoffs when relevant.
- Suggest simpler alternatives if they exist.
- Push back if the request leads to overcomplication.

**Do not start coding if requirements are ambiguous.**

---

## 2. Simplicity First

Write the minimum code needed to solve the problem.

Avoid:

- Unrequested features
- Premature abstractions
- Generalization for future use
- Overly defensive error handling

Guidelines:

- If code can be shorter and clearer, simplify it.
- Avoid writing reusable abstractions for one-time use.
- Ask: *"Is this the simplest solution a senior engineer would accept?"*

---

## 3. Surgical Changes

When modifying existing code:

- Change only what is necessary.
- Do not refactor unrelated code.
- Do not improve formatting or style outside the scope.
- Match the existing code style.

You may:

- Remove unused code ONLY if your changes introduced it.
- Mention (but do not fix) unrelated issues.

**Rule:** Every change must directly relate to the user's request.

---

## 4. Goal-Driven Execution

Convert tasks into verifiable goals.

Examples:

- "Fix bug" → Write a failing test, then make it pass
- "Add validation" → Define invalid cases and verify behavior
- "Refactor" → Ensure behavior remains unchanged

For multi-step tasks:

1. Define steps clearly
2. Add verification criteria per step
3. Iterate until all checks pass

Avoid vague goals like:
- "make it better"
- "clean up code"

---

## Expected Behavior

This skill is working correctly if:

- Fewer unnecessary changes appear in diffs
- Code remains simple and focused
- Clarifying questions are asked early
- Overengineering is avoided
- Changes are minimal and intentional

---

## Example Usage

**User request:** "Refactor this function"

**With this skill:**

1. Ask: What is the goal of the refactor?
2. Define success criteria (e.g., readability, performance)
3. Ensure no behavior changes
4. Apply minimal changes only

---

