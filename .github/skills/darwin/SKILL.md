---
name: darwin
description: Detects project health, agent relevance, and evolution opportunities. Use when evaluating system quality, identifying inefficiencies, or deciding what to improve, remove, or simplify.
---

## Overview

This skill evaluates system health and evolution opportunities.

It helps detect:
- unnecessary complexity
- underused components
- coordination overhead
- misaligned architecture decisions

It focuses on **improving systems through small, evidence-based changes**.

---

## 1. Assess Before Changing

Before proposing improvements:

- Identify what currently exists
- Determine what is actually being used
- Distinguish between:
  - real problems
  - perceived problems

Ask:

- What is failing?
- What is slow or inefficient?
- What is unused or redundant?

**Do not propose changes without clear evidence.**

---

## 2. Detect Overengineering

Actively look for:

- Too many components solving one problem
- Layers that add no clear value
- Abstractions used only once
- Complex workflows where a simple one would work

If found:

- Suggest simplification
- Recommend consolidation
- Highlight unnecessary parts

Ask:

> "Could this be solved with fewer moving pieces?"

---

## 3. Evaluate Component Relevance

For each component (agent, module, service):

- Is it actively used?
- Does it provide unique value?
- Could another component replace it?

Classify:

- **Core** → essential
- **Useful** → helpful but not critical
- **Redundant** → overlaps with others
- **Unused** → no clear usage

Prefer removing over maintaining unused parts.

---

## 4. Identify Coordination Costs

More components = more overhead.

Watch for:

- Excessive handoffs
- Repeated transformations of the same data
- Long chains of responsibility
- Multiple steps that could be merged

If coordination cost is high:

- Suggest reducing steps
- Suggest merging responsibilities
- Suggest a simpler flow

---

## 5. Avoid the Multi-Agent Trap

Before recommending more components:

- Check if a single component can solve the problem
- Verify real need for separation

Avoid adding complexity when:

- tasks are sequential
- logic is tightly coupled
- communication overhead outweighs benefits

---

## 6. Propose Small, Safe Improvements

When suggesting changes:

- Prefer incremental improvements over rewrites
- Clearly state:
  - what changes
  - why it improves things
  - what risk it introduces

Good changes:

- removing unused components
- merging duplicate logic
- simplifying workflows

Avoid:

- large refactors without clear ROI
- redesigning entire systems unnecessarily

---

## 7. Validate Impact

For every proposal:

- Define expected improvement:
  - simpler structure
  - fewer steps
  - faster execution
  - easier maintenance

If impact is unclear:

**Do not proceed.**

---

## Expected Behavior

This skill is working correctly if:

- Systems become simpler over time
- Unused or redundant parts are removed
- Architecture decisions are justified
- Complexity is reduced, not increased
- Changes are small and intentional

---

## Example Usage

**User request:** "Do we need all these agents?"

**With this skill:**

1. List all agents
2. Classify their relevance
3. Identify overlaps
4. Recommend removals or merges
5. Justify each decision clearly

---
