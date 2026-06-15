---
name: ripple
description: Enforces structured pre-change impact analysis. Use before modifying code to evaluate dependency risk, blast radius, and consistency issues. Does not write code.
---

## Overview

This skill ensures every change is evaluated **before implementation** to avoid unintended side effects, breaking changes, and inconsistent patterns.

It prioritizes **risk awareness, dependency understanding, and controlled changes** over speed.

---

## 1. Define Scope First

Before analyzing impact:

- Clearly describe the change (what, where, why)
- Identify affected entry points (files, modules, APIs)
- Classify the change type:
  - Refactor
  - Rename
  - API change
  - Behavior change
  - Deletion

If scope is unclear:

- Ask for missing details
- Do not proceed with assumptions

**Rule:** No impact analysis without a clearly defined scope.

---

## 2. Trace Dependencies (Vertical Impact)

Map how the change propagates:

- L0 → File being changed
- L1 → Direct dependents
- L2 → Transitive dependents
- L3 → System-wide or shared module impact

Identify:

- Who calls this?
- What depends on it?
- What breaks if it changes?

Classify breaking changes:

- CRITICAL → API removal, schema change
- HIGH → Function signature change
- MEDIUM → Behavior change
- LOW → Internal-only change

**Rule:** Always trace at least to L2 (L3 if shared/core module).

---

## 3. Check Consistency (Horizontal Impact)

Ensure the change aligns with existing patterns:

- Naming conventions
- File structure
- API design
- Type usage

Flag deviations:

- HIGH → Breaks established conventions
- MEDIUM → Inconsistent with similar modules
- LOW → Minor differences

**Do not normalize patterns silently — only report inconsistencies.**

---

## 4. Evaluate Blast Radius

Estimate how large the impact is:

- Number of affected files
- Modules or services touched
- Cross-boundary effects (frontend/backend, services)

Key signals:

- ≥ 10 files → Medium risk
- ≥ 15 files → High risk (recommend PR split)
- Shared/core module → Amplified impact
- Multiple services → Cascade risk

Ask:

- "How far does this ripple go?"
- "What else breaks indirectly?"

---

## 5. Detect Cascading Effects

Look beyond direct dependencies:

- Sequential failures across modules
- Feedback loops between components
- Shared resource contention (DB, queues, cache)
- Timing/order issues (async flows)

Trigger when:

- Change touches multiple modules/services
- Dependencies are bidirectional
- Risk appears non-local

**Goal:** Identify second-order effects, not just direct ones.

---

## 6. Risk Scoring

Assign a risk score (1–10) based on:

- Scope (30%)
- Breaking potential (25%)
- Pattern deviation (20%)
- Test coverage (15%)
- Reversibility (10%)

Interpretation:

- 1–3 → LOW (safe)
- 4–6 → MEDIUM (watch)
- 7–8 → HIGH (needs mitigation)
- 9–10 → CRITICAL (block or redesign)

**Always justify the score.**

---

## 7. Recommendation (Go / No-Go)

Based on analysis:

- **GO** → Safe to proceed
- **CONDITIONAL GO** → Requires mitigations
- **NO-GO** → Too risky without redesign

Include:

- Required safeguards
- Testing needs
- Rollback considerations

---

## Expected Behavior

This skill is working correctly if:

- Risks are identified before coding starts
- Dependency chains are explicitly mapped
- Changes are scoped realistically
- Hidden impacts are surfaced early
- Large or risky changes are challenged

---

## Example Usage

**User request:** "Rename a shared API method"

**With this skill:**

1. Identify all consumers (L1, L2)
2. Detect breaking change (HIGH)
3. Evaluate affected files (e.g., 12 files)
4. Flag risk (HIGH)
5. Recommend:
   - Add backward compatibility layer
   - Update consumers incrementally
   - Add regression tests

---