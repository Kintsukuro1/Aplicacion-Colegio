---
name: sigil
description: Generates project-specific coding skills based on repository structure, tech stack, and conventions. Use when creating reusable prompts, workflows, or coding patterns tailored to a project.
---

## Overview

This skill generates reusable coding skills tailored to a specific project.

It analyzes:
- tech stack
- project structure
- coding conventions

Then creates **focused, practical skills** that improve developer productivity.

---

## 1. Analyze Before Generating

Before creating any skill:

- Identify the tech stack (frameworks, languages, tools)
- Detect project structure and patterns
- Observe naming, error handling, and testing style

Ask:

- What patterns repeat frequently?
- What tasks are complex or error-prone?
- What would benefit from reuse?

**Do not generate generic skills. Always adapt to the project.**

---

## 2. Generate Only High-Value Skills

Create skills only if they:

- solve a recurring problem
- reduce complexity or errors
- standardize important workflows

Avoid creating skills for:

- trivial tasks
- one-time operations
- already simple logic

Ask:

> "Will this save time repeatedly?"

---

## 3. Keep Skills Small and Focused

Each skill should:

- solve one clear problem
- be easy to understand
- be immediately usable

Prefer:

- short instructions
- concrete steps
- real examples

Avoid:

- long explanations
- abstract theory
- multi-purpose skills

---

## 4. Match Project Conventions

Every generated skill must:

- follow existing naming patterns
- use the same libraries and tools
- match code style and structure

Do not introduce:

- new frameworks
- different patterns
- conflicting conventions

---

## 5. Write Clear Activation Descriptions

Descriptions must explain **when to use the skill**, not just what it does.

Good description:

- "Generate API routes with validation and error handling following project patterns"

Bad description:

- "Helps with APIs"

Make descriptions:

- specific
- action-oriented
- aligned with real developer requests

---

## 6. Avoid Duplication

Before generating a skill:

- check if a similar pattern already exists
- avoid overlapping functionality

If overlap exists:

- improve the existing approach
- or merge into a single clearer skill

---

## 7. Prefer Practical Output

Every skill should produce:

- working code
- clear steps
- real usage patterns

Avoid:

- vague guidelines
- theoretical recommendations

---

## Expected Behavior

This skill is working correctly if:

- generated skills are reused frequently
- they match the project's real patterns
- they reduce repeated effort
- they stay simple and focused
- they improve consistency across the codebase

---

## Example Usage

**User request:** "Create a skill for handling API validation"

**With this skill:**

1. Analyze existing API patterns
2. Detect validation approach (e.g., Zod, Joi)
3. Generate a skill using the same structure
4. Ensure it matches project conventions
5. Keep it simple and reusable

---
