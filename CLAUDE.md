# CLAUDE.md

## Project
CS 440 lab: add an **Agent Skills** component (component 7) to rasbt's mini-coding-agent.
Everything is in `mini_coding_agent.py`. Tests are in `tests/`.

## Source of truth — read these first
1. `intend.md` — why, success criteria S1–S7
2. `spec.md` — requirements with IDs (R-DISC-*, R-TRIG-*, R-TOOL-*, R-EXEC-*, R-LOG-*, R-NF-*)
3. `plan.md` — exact integration points H1–H7 and the implementation order

Follow `plan.md` §5 in order. If code and spec disagree, stop and ask. Don't silently change the spec.

## Hard constraints
- Python **standard library only**. No new dependencies (R-NF-1).
- Don't change existing CLI flags, the session format, or existing tests (R-NF-2).
- All new behavior must be testable with `FakeModelClient`, with no Ollama required (R-NF-3).

## Commands
- Run all tests: `python -m pytest -q` (target after implementation: 22 passed, 1 skipped)
- Run only the new tests: `python -m pytest -q tests/test_skills.py`
- Live run (needs Ollama running locally):
  `python mini_coding_agent.py --cwd <workspace> --max-steps 15 --approval auto "<prompt>"`
- Skill log: `<workspace>/.mini-coding-agent/skills.log` (gitignored, so copy excerpts into `report.md`)

## Git workflow
- Work on the `agent-skills` branch.
- One commit per SDLC stage, in the order given in `plan.md` §8. Commit the tests (failing) **before** the implementation.
- Don't squash or rewrite history. The commit order is graded evidence of the SDLC.

## Important: don't do the lab's core task yourself
The goal is for **mini-coding-agent** (running a local Ollama model) to solve Lab 4 using the Lab 5 skill.
- Do NOT solve Lab 4 directly or write its solution files.
- Your role: implement the component, write `skills/<lab5-skill>/SKILL.md` from the Lab 5 material, launch the mini agent, and record what happens (including failures) in `report.md`.

## Naming note
The `skills/` folder in this repo holds skills for **mini-coding-agent**. It is unrelated to Claude Code's own `.claude/skills/`. Don't move or mix them.
