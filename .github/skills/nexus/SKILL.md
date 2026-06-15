---
name: nexus
description: Orchestrates multiple skills to solve complex tasks using structured thinking and minimal effective workflows.
---

## Overview

Nexus coordinates multiple skills to solve complex problems in a structured and efficient way.

It does NOT simulate multiple agents.  
Instead, it:

- Breaks problems into steps
- Selects the right skills
- Guides execution in order
- Ensures quality before final output

---

## 1. Core Behavior

When a task is complex:

1. Understand the goal
2. Break it into smaller steps
3. Assign the correct skill to each step
4. Execute step-by-step
5. Validate results before continuing

---

## 2. Minimum Viable Workflow

Always use the **simplest possible workflow**.

Rules:

- Start with one skill
- Add more only if necessary
- Avoid overengineering
- Keep steps clear and linear

---

## 3. Task Decomposition

Break tasks when:

- They involve multiple concerns (UI + backend + DB)
- They touch multiple files
- They require multiple steps

Output format:

1. Goal
2. Steps
3. Skills used per step

---

## 4. Skill Routing

Use this mapping:

- Bugs → debug + testing
- UI → frontend-design
- Database → database
- Security → security
- Features → orchestrator + thinking

---

## 5. Execution Rules

- Execute one step at a time
- Do not jump ahead
- Validate each step before continuing
- Keep changes minimal and controlled

---

## 6. Validation

Before finishing:

- Check if goal is achieved
- Verify no regressions
- Ensure code is production-ready

---

## 7. Output Structure

Always respond with:

### Plan
- Goal
- Steps
- Skills used

### Execution
- Step-by-step results

### Validation
- What was verified

---

## 8. Anti-Patterns

Avoid:

- Doing everything at once
- Mixing unrelated concerns
- Overcomplicated workflows
- Skipping validation

---

## Expected Behavior

This skill is working correctly if:

- Tasks are broken into clear steps
- The correct skills are used
- Output is structured and easy to follow
- Complexity is minimized

---

## Example Usage

User request:
"Fix login and improve UI"

With Nexus:

Plan:
1. Fix bug → debug
2. Improve UI → frontend-design

Execution:
- Step 1 → fix bug
- Step 2 → improve UI

Validation:
- Bug fixed
- UI improved
