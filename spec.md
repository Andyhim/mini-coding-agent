# Specification: Agent Skills Component

**SDLC stage:** 2 of 5 — Specification (intend.md → **spec.md** → plan.md → implementation + tests → report.md)
**Traces to:** success criteria S1–S7 in `intend.md`

Requirements use **MUST** / **SHOULD** / **MAY** (RFC 2119). Each one has an ID that tests and `report.md` refer back to.

---

## 1. Definitions

| Term | Meaning |
|------|---------|
| **Skill** | A folder holding a `SKILL.md` file that describes a reusable procedure |
| **Skills directory** | A top-level workspace folder named `skills/`, `skill/`, or `.skills/` |
| **Catalog** | The list of every discovered skill's `name: description` |
| **Active skill** | The skill whose full instructions are currently in the agent's prompt |
| **Similarity check** | The scoring of a prompt against every skill to decide whether one should trigger |

---

## 2. Skill file format

**R-FMT-1** A skill MUST be stored at `<workspace>/<skills-dir>/<skill-folder>/SKILL.md`. The filename match MUST be case-insensitive (`skill.md` is also accepted).

**R-FMT-2** `SKILL.md` MAY start with a frontmatter block between `---` lines, holding `key: value` pairs:

```markdown
---
name: pr-review
description: Review a pull request or code diff for bugs, style issues, and missing tests
triggers: review, pull request, diff, code review
---
1. Run `git diff` to see the changes.
2. List bugs, style issues, and missing tests.
3. Return a review summary.
```

| Field | Required | Default | Use |
|-------|----------|---------|-----|
| `name` | No | folder name | Unique ID; used by `use_skill` and for explicit mentions |
| `description` | Recommended | `""` | Shown in the catalog; used for similarity |
| `triggers` | No | none | Comma-separated keywords; used for similarity |

**R-FMT-3** Everything after the frontmatter MUST be treated as the skill's **instruction body**.

**R-FMT-4** Parsing MUST NOT require any third-party library (no PyYAML).

**R-FMT-5** Unknown frontmatter keys MUST be ignored. This lets a Claude Code skill keep keys such as `disable-model-invocation` without changing how this agent treats it. The component MUST NOT do argument substitution (such as Claude Code's `$ARGUMENTS`), so a ported skill must not depend on it.

**R-FMT-6** A skill folder MAY contain other files, such as `scripts/evaluate.py`. The component does not run or load them. The instruction body refers to them by workspace-relative path, and the agent runs them with the existing tools (`run_shell`), under the normal approval policy. This keeps intend.md §5 true: the component adds no special support for bundled scripts.

---

## 3. Functional requirements

### 3.1 Discovery (→ S1)

**R-DISC-1** At agent startup, the component MUST scan every skills directory that exists and register each valid skill.

**R-DISC-2** A folder without a `SKILL.md` MUST be skipped silently.

**R-DISC-3** If no skills are found, the agent MUST behave exactly like the original agent: no `use_skill` tool, the catalog shows `- none`, and nothing is written to `skills.log`.

### 3.2 Prompt-triggered activation (→ S2, S3)

**R-TRIG-1** On every user request (`MiniAgent.ask`), the component MUST run a similarity check between the request and every skill before the first model call.

**R-TRIG-2** Similarity MUST be the **cosine similarity of TF-IDF vectors**:
- **Prompt document:** the user request
- **Skill document:** `name` (with hyphens turned into spaces) + `description` + `triggers`
- **Tokenization:** lowercase, alphanumeric tokens, stopwords removed, tokens longer than 1 character
- **IDF:** `1 + ln((N + 1) / (1 + df))` over the skill documents

**R-TRIG-3** If the request contains a skill's name (e.g. `pr-review` or `/pr-review`), that skill's score MUST be set to **1.0** (explicit invocation).

**R-TRIG-4** The highest-scoring skill MUST be activated if its score is **≥ 0.20** (the `SKILL_THRESHOLD` constant). Otherwise no skill is activated.

**R-TRIG-5** If no skill has been activated yet in the current agent instance, the prompt MUST contain `Active skill: none`. A skill that is already active stays active on later requests until another skill replaces it (R-EXEC-4).

### 3.3 Agent-triggered activation (→ S4)

**R-TOOL-1** When at least one skill exists, the agent MUST expose a tool:

```
use_skill(name: str) [safe] — Load an agent skill's SKILL.md instructions by name and follow them.
```

**R-TOOL-2** `use_skill` MUST be marked **not risky** (no approval prompt), since it only reads.

**R-TOOL-3** Validation MUST reject an unknown skill name with an error that lists the available skills.

**R-TOOL-4** On success, the tool MUST activate the skill and return its instruction body as the tool result.

### 3.4 Execution / context injection

**R-EXEC-1** The stable prompt prefix MUST include the **catalog only** (names and descriptions), never full skill bodies. This preserves prefix cache reuse (component 2).

**R-EXEC-2** When a skill is active, its full body MUST be injected into the *dynamic* part of the prompt, after memory and before the transcript, in this form:

```
Active skill: <name> (from <relative path>)
Follow these instructions step by step:
<body>
```

**R-EXEC-3** Activation MUST add the note `skill active: <name>` to working memory (component 5).

**R-EXEC-4** Only one skill MAY be active at a time. A new activation replaces the previous one.

### 3.5 Logging (→ S5)

**R-LOG-1** Every log entry MUST be appended as one JSON object per line (JSONL) to `<workspace>/.mini-coding-agent/skills.log`. The directory MUST be created if it is missing.

**R-LOG-2** Every similarity check MUST log:

```json
{"created_at": "<ISO-8601 UTC>", "event": "similarity_check", "source": "prompt",
 "prompt": "<full user request>", "scores": {"<skill>": 0.6489, "...": 0.0},
 "threshold": 0.2, "selected": "<skill name or null>"}
```
`scores` MUST include **every** skill, sorted from highest to lowest.

**R-LOG-3** Every activation (by prompt or by tool) MUST log:

```json
{"created_at": "<ISO-8601 UTC>", "event": "skill_executed",
 "trigger": "prompt | agent", "skill": "<name>", "path": "skills/<folder>/SKILL.md"}
```

---

## 4. Non-functional requirements

**R-NF-1 Dependencies:** Python standard library only.
**R-NF-2 Compatibility:** All existing tests MUST still pass (→ S6). The CLI flags and session format MUST NOT change.
**R-NF-3 Testability:** All behavior MUST be testable with `FakeModelClient` (no Ollama needed).
**R-NF-4 Performance:** Similarity checks SHOULD take under 10 ms for 50 or fewer skills.
**R-NF-5 Transparency:** Every trigger decision MUST be reconstructable from `skills.log` alone.

---

## 5. Acceptance tests

| Test (`tests/test_skills.py`) | Requirements | Criterion |
|-------------------------------|--------------|-----------|
| `test_discovers_skill_folder` | R-FMT-1, R-FMT-5, R-DISC-1–3, R-TOOL-1, R-TOOL-2, R-EXEC-1 | S1 |
| `test_prompt_triggers_skill_and_logs` | R-TRIG-1–4, R-EXEC-2, R-EXEC-3, R-LOG-1–3 | S2, S5 |
| `test_unrelated_prompt_does_not_trigger` | R-TRIG-4, R-TRIG-5, R-LOG-2 | S3 |
| `test_agent_can_invoke_skill_mid_task` | R-TOOL-1–4, R-FMT-5, R-LOG-3 | S4 |
| Existing `tests/test_mini_coding_agent.py` | R-NF-2 | S6 |
| Live Lab 4 run (documented in `report.md`) | all, R-LAB-1–5 | S7 |

---

## 6. Known limitations (accepted for this version)

- **Lexical matching only:** Paraphrased prompts that share no words with a skill won't trigger it automatically. The mitigations are `triggers`, explicit mention, and the `use_skill` fallback.
- **Explicit-mention matching is a substring check:** A skill with a very short name could match by accident inside unrelated words. Use descriptive, hyphenated names.
- **Skills are sticky within a run:** In interactive mode, a skill stays active on later unrelated requests until another one replaces it. A future version could clear the active skill when a new request scores below the threshold.
- **Active skill is not saved with the session:** On `--resume`, the skill is chosen again by the next prompt.
- **Skills are found only inside the workspace:** The agent scans the `--cwd` workspace, not this repo. To use a skill from this repo on another project, copy its folder into that project's `skills/` (see R-LAB-4).
- **Child agents run their own similarity check:** A `delegate` child is a full `MiniAgent`, so its task is also checked and logged with `source: "prompt"`. Read consecutive entries with that in mind.
- **Small local models** may not follow skill steps faithfully. This is model behavior, not a component defect, and it is recorded in `report.md`.

---

## 7. Lab 4 run with the Lab 5 skill (→ S7)

Lab 4 asks for tabular Q-learning for the vacuum agent in `vacuum_world_lab3.ipynb` (the AIMA vacuum-world repo). Lab 5 produced the Claude Code skill `.claude/skills/evaluate-agent/`, which reviews the Q-learning code, runs `scripts/evaluate.py`, and checks a "learned" definition. These requirements cover porting that skill and the live run.

**R-LAB-1** The Lab 5 skill MUST be ported to `skills/evaluate-agent/` as an **evaluate-and-fix loop**. It keeps the Lab 5 review checklist, experiment script, "learned" definition, and summary format. It adds one rule: if the solution is missing, or fails the review or the "learned" check, the agent writes or fixes it and then evaluates again.

**R-LAB-2** The agent MUST write its Q-learning code to `lab4_solution.py` in the workspace root. The notebook MUST NOT be edited, since a small model can't reliably patch 61 KB of notebook JSON.

**R-LAB-3** `SKILL.md` MUST contain the environment description from the Lab 5 version of the project's CLAUDE.md, the reference Q-learning pseudocode from the Lab 5 `algorithm-reviewer`, and the interface the experiment script calls: `q_learning(env, n_episodes, alpha, epsilon)` returning `(q, policy)`. It MUST NOT contain a Q-learning implementation. As in Lab 5, hyperparameter values come only from the experiment step (the script's defaults and one-at-a-time changes).

**R-LAB-4** The experiment script MUST run the notebook's Lab 3 code cells, then `lab4_solution.py`, and compare the result with `value_iteration`. It MUST use only packages that are already installed (the standard library and numpy).

**R-LAB-5** The live run MUST happen in a separate clone of the vacuum-world repo, checked out at the Lab 4 starting commit, with no git remote. The run uses `--approval auto`, so this keeps the model from pushing anywhere.
