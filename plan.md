# Plan: Agent Skills Component

**SDLC stage:** 3 of 5 — Design / Plan (intend.md → spec.md → **plan.md** → implementation + tests → report.md)
**Implements:** requirements in `spec.md`

---

## 1. Architecture overview

The skills component is added as **component 7**, next to the six existing ones in `mini_coding_agent.py`. It sits between the user request and the prompt builder. It also exposes one tool through the existing tool system (component 3).

```
                ┌──────────────────────────────┐
 user request ─►│ MiniAgent.ask()              │
                │  1. record user message      │
                │  2. SkillRegistry.match() ───┼──► skills.log  (similarity_check)
                │  3. activate_skill() if hit ─┼──► skills.log  (skill_executed, trigger=prompt)
                │  4. agent loop               │
                └──────────────┬───────────────┘
                               ▼
                ┌──────────────────────────────┐
                │ MiniAgent.prompt()           │
                │  prefix  (static, cached)    │◄── skill CATALOG (names + descriptions)
                │  memory                      │
                │  skill_text()  (dynamic)     │◄── ACTIVE skill body
                │  transcript                  │
                │  current request             │
                └──────────────┬───────────────┘
                               ▼
                         model.complete()
                               │ <tool>{"name":"use_skill",...}</tool>
                               ▼
                ┌──────────────────────────────┐
                │ tool_use_skill()             │──► skills.log  (skill_executed, trigger=agent)
                └──────────────────────────────┘
```

**Key design decision (progressive disclosure):** The catalog is small and rarely changes, so it goes in the **static prefix**. Skill bodies are large and depend on the task, so they go in the **dynamic** section. That way activating a skill never invalidates the cached prefix (component 2).

---

## 2. Files changed

| File | Change | Approx. size |
|------|--------|--------------|
| `mini_coding_agent.py` | New section 7 (helpers, `Skill`, `SkillRegistry`), plus small hooks in `MiniAgent` | +~150 lines |
| `tests/test_skills.py` | **New** — 4 acceptance tests | ~120 lines |
| `skills/evaluate-agent/SKILL.md` | **New** — the Lab 5 skill, ported (§9) | — |
| `skills/evaluate-agent/scripts/evaluate.py` | **New** — the Lab 5 experiment script, adapted (§9.2) | ~130 lines |
| `skills/pr-review/SKILL.md` | **New** — the spec's example skill. It gives the similarity check a second candidate, so the log shows the matcher choosing between skills instead of scoring one. | ~10 lines |
| `report.md`, `logs/lab4-run.jsonl` | **New** — live-run write-up and the copied `skills.log` lines | — |
| `.gitignore` | No change. `.mini-coding-agent` is already ignored, so `skills.log` won't be committed. Copy the relevant log lines into `logs/lab4-run.jsonl` as evidence. | — |

`Lab5/` (the vacuum-world repo, which is its own git repo) currently sits inside this folder for reference. It is never committed here; stage files by name.

There are no new dependencies. The only new import is `math`, which is in the standard library.

---

## 3. New code: section 7 "Agent Skills"

This goes directly **above `class MiniAgent`**, so the class can reference it.

### 3.1 Module-level constants and helpers

| Name | Purpose | Spec |
|------|---------|------|
| `SKILL_DIRS = ("skills", "skill", ".skills")` | Folders to scan | R-FMT-1 |
| `SKILL_THRESHOLD = 0.20` | Activation cutoff | R-TRIG-4 |
| `STOPWORDS` | Common words dropped during tokenization | R-TRIG-2 |
| `tokenize(text)` | Lowercase alphanumeric tokens, stopwords removed, length > 1 | R-TRIG-2 |
| `cosine(a, b)` | Cosine similarity of two sparse dict vectors | R-TRIG-2 |

### 3.2 `class Skill`

A plain data holder: `name`, `description`, `body`, `path`, `triggers`.

### 3.3 `class SkillRegistry`

| Method | Responsibility | Spec |
|--------|----------------|------|
| `__init__(root, log_path, threshold)` | Discover skills, build the IDF table | R-DISC-1 |
| `discover()` | Walk `SKILL_DIRS/*/SKILL.md` (case-insensitive) and build a `Skill` for each | R-FMT-1, R-DISC-1/2 |
| `parse_skill_file(text)` *(static)* | Split the `---` frontmatter into a dict and return `(meta, body)` | R-FMT-2/3/4 |
| `skill_text(skill)` | `name` (hyphens → spaces) + `description` + `triggers` | R-TRIG-2 |
| `build_idf()` | `1 + ln((N+1)/(1+df))` over skill documents | R-TRIG-2 |
| `vector(text)` | TF-IDF dict for a text | R-TRIG-2 |
| `scores(prompt)` | Cosine score for every skill; explicit name mention → 1.0; sorted highest first | R-TRIG-2/3, R-LOG-2 |
| `match(prompt, source)` | Pick the best skill if it reaches the threshold; **log `similarity_check`**; return the `Skill` or `None`. With no skills, return `None` and log nothing. | R-TRIG-4, R-LOG-2, R-DISC-3 |
| `catalog()` | `- name: description` lines, or `- none` | R-EXEC-1, R-DISC-3 |
| `log(entry)` | Add a timestamp and append one JSON line to `skills.log` | R-LOG-1 |

**Why the registry is its own class:** It has no dependency on `MiniAgent`, so it can be unit-tested by itself and reused by child agents created through `delegate`.

---

## 4. Hooks into `MiniAgent`

Each change is small and leaves existing behavior alone when there are no skills (R-DISC-3, R-NF-2).

| # | Location | Change | Spec |
|---|----------|--------|------|
| H1 | `__init__`, **before** `self.tools = self.build_tools()` | `self.skills = SkillRegistry(self.root, self.root / ".mini-coding-agent" / "skills.log")` and `self.active_skill = None`. This must come first because `build_tools` and `build_prefix` read the registry. | R-DISC-1 |
| H2 | `build_tools()`, before the `delegate` block | Register `use_skill` (`schema {"name": "str"}`, `risky: False`), but only if `self.skills.skills` is not empty | R-TOOL-1/2, R-DISC-3 |
| H3 | `build_prefix()`, after the examples section | Add `"Agent skills (call use_skill when one fits the task):\n" + self.skills.catalog()` | R-EXEC-1 |
| H4 | `prompt()`, between `memory_text()` and the transcript | Insert `self.skill_text()` | R-EXEC-2 |
| H5 | `ask()`, right after the user message is recorded | `skill = self.skills.match(user_message, source="prompt")`; if there's a hit → `self.activate_skill(skill, trigger="prompt")` | R-TRIG-1/4 |
| H6 | `validate_tool()`, before the `delegate` branch; `tool_example()` | If `name == "use_skill"` and the name is unknown → `ValueError` listing the available skills. Add a `use_skill` entry to `tool_example()`, so the error shows a correct call like every other tool. | R-TOOL-3 |
| H7 | New methods, placed before `tool_delegate` | `skill_text()`, `activate_skill(skill, trigger)`, `tool_use_skill(args)` | R-EXEC-2/3/4, R-TOOL-4, R-LOG-3 |

### New `MiniAgent` methods (H7)

- **`skill_text()`** — Returns `"Active skill: none"`, or the active skill's header, path, and body in the R-EXEC-2 format.
- **`activate_skill(skill, trigger)`** — Sets `self.active_skill`, adds the note `skill active: <name>` to memory, and **logs `skill_executed`**. This is the only place where execution gets logged, so both trigger paths log the same way.
- **`tool_use_skill(args)`** — Looks up the skill (already validated), calls `activate_skill(..., trigger="agent")`, and returns the body as the tool result.

---

## 5. Implementation order

1. **Tests first:** add `tests/test_skills.py` and confirm the 4 new tests fail with an `ImportError` on `SkillRegistry`.
2. Add `import math` and the constants and helpers (§3.1).
3. Add `Skill` and `SkillRegistry` (§3.2–3.3).
4. Add hooks H1, H6 and H7, then H2–H5.
5. Run the full suite. Target: **22 passed, 1 skipped** (18 existing + 4 new).
6. Port the Lab 5 skill to `skills/evaluate-agent/` (§9) and add `skills/pr-review/SKILL.md`. Check that the adapted `evaluate.py` still reproduces the Lab 5 baseline when it's given the Lab 5 solution code (§9.2).
7. Do the live Lab 4 run with Ollama (§10) and capture `skills.log` for `report.md`.

---

## 6. Test plan

| Level | What | How |
|-------|------|-----|
| Unit / acceptance | Discovery, prompt trigger, no false positive, agent trigger, log format | `tests/test_skills.py` with `FakeModelClient` (spec §5) |
| Regression | Original behavior unchanged | Existing `tests/test_mini_coding_agent.py` |
| Integration (manual) | A real model solves Lab 4 using the Lab 5 skill | §10 |
| Trigger-path demo | Show both trigger paths live | Run 1: a prompt worded to match the skill (→ `trigger: prompt`). Run 2: a vague prompt (→ hopefully `trigger: agent`) |

**Commands**
```bash
python -m pytest -q                         # all tests
python -m pytest -q tests/test_skills.py    # only the new component
```

On the development machine (Windows), `python` is a Microsoft Store stub and the system Python has no pytest, so use:
```bash
uv run --python 3.12 --with pytest python -m pytest -q
```

---

## 7. Design alternatives considered

| Alternative | Why it was not chosen |
|-------------|-----------------------|
| Embedding similarity (Ollama `/api/embeddings`) | Better at catching paraphrases, but needs a running server for the tests and an extra model pull. **Future work.** |
| Ask the LLM to choose the skill | Costs an extra model call on every request, isn't deterministic, and is hard to unit-test |
| Put full skill bodies in the prefix | Wastes context and grows with the number of skills. The catalog-only prefix scales better. |
| PyYAML for frontmatter | Would break the repo's no-dependencies constraint (R-NF-1) |
| Run skills as subagents (`delegate`) | Child agents are read-only and limited in depth, but Lab 4 skills may need to write files |

---

## 8. Commit plan (SDLC evidence)

```
SDLC: intent                    intend.md
SDLC: specification             spec.md
SDLC: plan                      plan.md
test: skills acceptance tests   tests/test_skills.py        (red)
feat: agent skills component    mini_coding_agent.py        (green)
feat: lab 5 skill               skills/<lab5-skill>/SKILL.md
docs: lab 4 run + report        report.md, skills.log excerpt
```

**As executed:** the intent, specification, and plan landed together in one commit (`4a460d2`). History isn't rewritten, so that stays as is. After the Lab 4 and Lab 5 material was reviewed, a separate commit refined the spec (R-FMT-5/6, R-LAB-*) and this plan (§9, §10). The rest of the order is unchanged:

```
SDLC: intent + specification + plan       intend.md, spec.md, plan.md   (4a460d2)
docs: refine spec and plan for Lab 4/5    spec.md, plan.md
test: skills acceptance tests             tests/test_skills.py          (red)
feat: agent skills component              mini_coding_agent.py          (green)
feat: port lab 5 evaluate-agent skill     skills/evaluate-agent/, skills/pr-review/
docs: lab 4 run + report                  report.md, logs/lab4-run.jsonl
```

---

## 9. Porting the Lab 5 skill

### 9.1 What changes, and why

| Lab 5 (Claude Code) | Mini-agent port | Why |
|---------------------|-----------------|-----|
| `SKILL.md` steps: reviewer, then experiments, then summary | Same three steps, written for this agent's tools, plus step 0: if `lab4_solution.py` is missing, write it to the interface. Also a fix rule: if the review or the "learned" check fails, patch and rerun (R-LAB-1). | The user chose an evaluate-and-fix loop |
| `algorithm-reviewer` subagent | Inline checklist step: read `lab4_solution.py` and check the update rule, terminal handling, all four actions, sampled next state, rewards, and the greedy policy | A small model follows an inline checklist more reliably than a `delegate` call limited to 3 steps |
| `experiment-runner` subagent | `run_shell` step that runs the experiment script | `delegate` children are read-only and can't run shell commands |
| `scripts/evaluate.py` | Adapted copy (§9.2) | New location, new solution file, Windows |
| CLAUDE.md environment description (Lab 5 version) | "Environment" section in `SKILL.md`, plus the `GridWorldMDP` methods the code needs | The agent auto-reads AGENTS.md and README.md, not CLAUDE.md. The Lab 4-era CLAUDE.md models dirt, which contradicts the Lab 3 code. |
| Reference pseudocode in `algorithm-reviewer` | Copied into `SKILL.md` | R-LAB-3 |
| `disable-model-invocation: true` | Dropped | The assignment needs the agent to invoke the skill itself. It would be ignored anyway (R-FMT-5). |
| `$ARGUMENTS` | "Use any settings given in the user's request" | No substitution (R-FMT-5) |
| Hooks (`confirm_git.py`, `check_notebook.py`) | Not ported | The approval policy already gates risky tools, and the notebook isn't edited (R-LAB-2) |

### 9.2 `evaluate.py` changes

- `REPO_ROOT` goes up **3** levels (`skills/evaluate-agent/scripts/`) instead of 4 (`.claude/skills/evaluate-agent/scripts/`).
- After running the notebook's Lab 3 code cells, it also runs `lab4_solution.py` in the same namespace. If the file is missing or fails to import, it prints a short, clear error instead of a long traceback, so the agent can act on it.
- It defines `goal_rate` and `mean_steps` itself. In Lab 5, `goal_rate` was part of the solution cells, so the agent now only has to write `q_learning`.
- Usage text says `py -3` (`python3` is a Store stub on this machine; Python 3.12 there has numpy).
- **Regression check:** with the Lab 5 solution saved as a temporary `lab4_solution.py`, the adapted script must reproduce the Lab 5 baseline. That baseline is 5 seeds, `alpha=0.05`, `epsilon=0.9`, 5000 episodes: goal rate 99.7–99.9% vs. 100% optimal, mean value error 0.11–0.16, about 6 s. Delete the temporary file afterwards. It is never committed or put in the live-run workspace.

---

## 10. Live-run procedure (S7)

1. **Workspace (R-LAB-5):** clone the vacuum-world repo to `CS440/lab4-run/`, check out a branch at `0f50818` (the Lab 4 starting point, notebook cells 0–52), and remove the `origin` remote. Each git step is confirmed with the user first.
2. **Install the skills:** copy this repo's `skills/` folder into `lab4-run/skills/`.
3. **Context check:** the client doesn't set `num_ctx`. After the first request, run `ollama ps`. If the context is too small for the prompt, set `OLLAMA_CONTEXT_LENGTH` on the Ollama server and restart it. This needs no CLI change.
4. **Run 1 (prompt trigger):**
   `py -3 mini_coding_agent.py --cwd ../lab4-run --max-steps 15 --max-new-tokens 1024 --approval auto "<prompt that names Q-learning and evaluation>"`
5. **Run 2 (agent trigger):** reset the workspace to `0f50818`, then use a vague prompt that doesn't match the skill well. Hope the agent calls `use_skill` itself.
6. **Independent check:** run `py -3 skills/evaluate-agent/scripts/evaluate.py --seeds 5` in `lab4-run` myself, and compare the output with the agent's claims.
7. **Evidence:** copy `lab4-run/.mini-coding-agent/skills.log` lines to `logs/lab4-run.jsonl`, and write `report.md`: prompts, similarity scores, executed skill, what the agent did, the final evaluation table, and failures.
