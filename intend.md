# Intent: Agent Skills Component for Mini-Coding-Agent

**SDLC stage:** 1 of 5 — Intent (→ spec.md → plan.md → implementation + tests → report.md)
**Author:** Andy
**Course:** CS 440 — Lab 6 <!-- fix lab number -->
**Date:** 2026-11-19

## 1. Problem

[mini-coding-agent](https://github.com/rasbt/mini-coding-agent) follows the coding-agent component architecture from class. It has six components:

1. Live repo context
2. Prompt shape and cache reuse
3. Structured tools, validation, and permissions
4. Context reduction and output management
5. Transcripts, memory, and resumption
6. Delegation and bounded subagents

It has **no agent skills component**, so it has no way to load reusable, task-specific procedures. Right now, every multi-step workflow (for example, reviewing a PR) has to be spelled out again in each prompt. The other option is to hard-code it into the system prompt, which bloats every model call and invalidates the cached prefix.

## 2. Goal

Add a seventh component, **Agent Skills**, that lets the agent:

- **Discover** skill folders in the workspace (e.g. `skills/pr-review/SKILL.md`)
- **Decide** when a skill is relevant, either from the user's prompt or on its own during execution
- **Execute** the skill by loading its `SKILL.md` instructions into context and following them
- **Log** every decision: the prompt, the similarity check, and the skill that ran

## 3. Motivation

- **Reuse:** A procedure is written once and used on many tasks.
- **Context efficiency:** Only skill names and descriptions sit in the stable prompt prefix. A full skill body is loaded only when it's needed (progressive disclosure). This keeps component 2 (cache reuse) intact.
- **Transparency:** Logged similarity scores make every trigger decision auditable and easy to debug.

## 4. Success criteria

| # | Criterion | How it will be verified |
|---|-----------|-------------------------|
| S1 | The agent finds every `<skills-dir>/<name>/SKILL.md` | Unit test |
| S2 | A relevant prompt triggers the matching skill automatically | Unit test + log entry |
| S3 | An unrelated prompt does **not** trigger a skill | Unit test |
| S4 | The agent can load a skill partway through a task with a tool call | Unit test + log entry |
| S5 | The log records the prompt, similarity scores, and the executed skill | Inspect `.mini-coding-agent/skills.log` |
| S6 | All existing tests still pass | `pytest` |
| S7 | Lab 4 is solved by the agent using the Lab 5 skill | Live run with Ollama + report.md |

## 5. Scope

**In scope**
- Skill discovery, prompt-based and agent-initiated triggering, and JSONL logging
- A lexical similarity check (TF-IDF cosine) using only the standard library
- Using the Lab 5 skill to solve Lab 4

**Out of scope**
- Matching by embeddings or an LLM (noted as future work)
- Skills that bundle their own scripts or resources
- Multiple skills active at the same time, or skills that call other skills
- Any new third-party dependencies

## 6. Constraints and assumptions

- Python standard library only, matching the original repo
- Must not break the existing CLI, sessions, or tests
- Runs against a small local Ollama model (default `qwen3.5:4b`). The model may follow skill instructions imperfectly, and that is a risk to record, not hide.

## 7. Risks

| Risk | Mitigation |
|------|-----------|
| Lexical matching misses paraphrased prompts | `triggers` keywords in frontmatter, explicit `/skill-name` mention, and an agent-invoked `use_skill` tool as a fallback |
| False-positive triggers | Similarity threshold (0.20) plus a negative test case; log scores to tune it |
| Small model ignores or drifts from the skill steps | Numbered, tool-specific steps in SKILL.md; raise `--max-steps`; document the outcome |
